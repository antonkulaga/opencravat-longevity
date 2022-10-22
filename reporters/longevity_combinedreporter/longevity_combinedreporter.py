from cravat.cravat_report import CravatReport
import sys
import datetime
import re
import csv
import zipfile
from pathlib import Path
cur_path = str(Path(__file__).parent)
sys.path.append(cur_path)
import templater
import longevitymap_report
import cancer_report
import prs_report
import drugs_report
import coronary_report
import pathlib

class Reporter(CravatReport):
    longevitymap = longevitymap_report.LongevitymapReport()
    cancer = cancer_report.CancerReport()
    prs = prs_report.PrsReport()
    drugs = drugs_report.DrugsReport()
    coronary = coronary_report.CoronaryReport()
    reports = [longevitymap, cancer, prs, drugs, coronary]
    anotators_dependency = ["dbsnp", "clinvar", "omim", "ncbigene", "pubmed", "gnomad", "longevitymap"]
    dependency_message = ""

    template_text = ""
    sorts = {"LONGEVITY":{"key":"WEIGHT", "type":"float", "reverse":"True"}, "CORONARY":{"key":"WEIGHT", "type":"float", "reverse":"True"}}
    data = {}
    template_vars = {}
    for rep in reports:
        data[rep.data_name()] = rep.data()

    current_level = ""
    columns = {}


    def __init__(self, args):
        super().__init__(args)
        for rep in self.reports:
            rep.init(self)


    def col_info(self, level):
        columns_arr = self.colinfo[level]['columns']
        modules_arr = self.colinfo[level]['colgroups']

        columns = {}
        modules = {}
        for module in modules_arr:
            if module.get('lastcol') != None and module.get('count') != None:
                if module['name'] == 'base':
                    module['start'] = module['lastcol'] - module['count']
                else:
                    module['start'] = module['lastcol'] - module['count'] - 1
            else:
                 module['start'] = module['start_column_number']

            modules[module['name']] = module

        for col in columns_arr:
            mod_name = col['col_name'].split("__")[0]
            ind = -1
            if modules.get(mod_name) != -1:
                if col['col_index'] is not None:
                    ind = modules[mod_name]['start'] + col['col_index']
                else:
                    ind = modules[mod_name]['start']

            column = {'name':col['col_name'], 'title':col['col_title'], 'ind':ind, 'col_index':col['col_index']}
            columns[col['col_name']] = column

        return columns

    def get_color(self, w, scale = 1.5):
        w = float(w)
        if w < 0:
            w = w * -1
            w = 1 - w * scale
            if w < 0:
                w = 0
            color = format(int(w * 255), 'x')
            if len(color) == 1:
                color = "0" + color
            color = "ff" + color + color
        else:
            w = 1 - w * scale
            if w < 0:
                w = 0
            color = format(int(w * 255), 'x')
            if len(color) == 1:
                color = "0" + color
            color = color + "ff" + color

        return color


    def setup(self):
        # setup is called first. Use it to open output files
        # Make output paths by appending to self.savepath
        self.dictrow = True
        outpath = f'{self.savepath}.longevity_combined.html'
        self.outfile = open(outpath, 'w', encoding='utf-8')
        with open(cur_path+"/template.html") as f:
            self.template_text = f.read()

        for rep in self.reports:
            rep.setup()


    def write_header(self, level):
        # write_header is called once per level. Use it to write
        # header lines, such as the top row of a csv, naming each column.
        # Use the self.colinfo object to get information about what
        # columns are present.
        # self.colinfo[level]['colgroups'] contains information about each
        # module (annotator) in the order it appears in the results.
        # self.colinfo[level]['columns'] contains information about each column
        # in the order it appears in the results
        self.current_level = level

        if level == 'variant':
            self.columns = self.col_info(level)
            self.columns['vcfinfo__zygosity']['ind'] += 3
            # print(self.colinfo[level]['colgroups'])
            # print(self.columns)

            dependency = list(self.anotators_dependency)

            for module in self.colinfo[level]['colgroups']:
                if module['name'] in dependency:
                    dependency.remove(module['name'])
                if module['name'] == 'longevitymap':
                    self.longevitymap.setActive()

            if len(dependency) > 0:
                self.dependency_message = "Error, there is no some of important anotators for correct functionality. " \
                                          "Add them and rerun this report. Anotators missing: "+", ".join(dependency)

                    # print("Is longevity True")
            # fields = ['base__chrom', 'base__pos', 'base__hugo', 'dbsnp__rsid', 'base__cchange',
            #           'vcfinfo__zygosity', 'gnomad__af', 'clinvar__disease_names', 'clinvar__sig', 'ncbigene__ncbi_desc']
            # for field in fields:
            #     print(self.columns[field])

    def get_value(self, row, name):
        if hasattr(self, "dictrow") and self.dictrow:
            val = row.get(name)
            if val is None:
                return ''
            return val
        col = self.columns.get(name)
        if col is not None:
            ind = col["ind"]
            if ind == -1:
                return ''
            else:
                return row[ind]
        return ''


    def write_table_row(self, row):
        # write_table_row is called once for each variant. row is a list of
        # values. The order or row matches with self.colinfo[level]['columns']
        # Write the data to the output file here.
        if self.current_level != 'variant':
            return

        for rep in self.reports:
            rep.process_row(row)


    def end(self):
        # end is called last. Use it to close the output file and
        # return a path to the output file.

        for rep in self.reports:
            rep.end()
        self.template_vars["LONGEVITYCOUNT"] = str(len(self.data["LONGEVITY"]["SNP"]))
        self.template_vars["DEPENDENCYERROR"] = self.dependency_message
        self.template_vars["DISPLAYERROR"] = "none"
        if self.dependency_message != "":
            self.template_vars["DISPLAYERROR"] = ""
        text = templater.replace_symbols(self.template_text, self.template_vars)
        text = templater.replace_loop(text, self.data, self.sorts)
        self.outfile.write(text)
        self.outfile.close()
        return Path(self.outfile.name).resolve()


### Don't edit anything below here ###
def main():
    reporter = Reporter(sys.argv)
    reporter.run()


if __name__ == '__main__':
    main()