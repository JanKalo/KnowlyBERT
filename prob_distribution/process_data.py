from html.parser import HTMLParser
import urllib.request as urllib
import numpy as np
import os
from matplotlib import pyplot as mp
import bisect 
import pyodbc
import json

# Specifying the ODBC driver, server name, database, etc. directly
cnxn = pyodbc.connect('DRIVER={/home/fichtel/virtodbc_r.so};HOST=134.169.32.169:1112;DATABASE=Virtuoso;UID=dba;PWD=F4B656JXqBG')
cnxn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
cnxn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
# Create a cursor from the connection
cursor = cnxn.cursor()

#HTML Parser
class MyHTMLParser(HTMLParser):
   #Initializing lists fpr properties
   props = list()
   #HTML Parser Methods
   def handle_starttag(self, startTag, attrs):
      if startTag == "td":
         for attr in attrs:
            self.props.append("P"+attr[1])

#parsing the properties website of wikidata and saves the properties in a list (format: P...)
def html_parser():
   parser = MyHTMLParser()
   html_page = str((urllib.urlopen("https://www.wikidata.org/wiki/Wikidata:Database_reports/List_of_properties/all")).read())
   parser.feed(html_page)
   return parser.props

def execute(prop):
   query =  """SELECT DISTINCT ?var (COUNT(*) as ?count)
                     WHERE {{
                        ?var <http://www.wikidata.org/prop/direct/{}> ?var2
                     }}
                     GROUP BY ?var""".format(prop)
   cursor.execute("SPARQL "+query)
   amount_results = 0
   all_data = []
   all_bins = []
   #save all numbers to the array "data" and the consisting bins into the sorted array "all_bins"
   while True:
      row = cursor.fetchone()
      if not row:
         break
      amount_results = amount_results + 1
      actu = int((row.count).replace('\x00', '')) #TODO WHY????
      all_data.append(actu)
      if actu not in all_bins:
         bisect.insort(all_bins, actu)
   if amount_results != 0:
      #create complete_bin array, that there are no gaps
      complete_bins = []
      for i in range(np.amin(all_bins),np.amax(all_bins)+1):
         complete_bins.append(int(i))
      #create dictio_bin_percentage
      n = len(all_data) #number of results
      dictio = {}
      for bins in complete_bins:
         dictio[bins] = 0 #initialized with 0
      for data in all_data:
         dictio[data] = dictio[data] + 1 #add number group by bin (e.g. {2: 3000}, 3000 entities have 2 results)
      for bins in dictio:
         dictio[bins] = dictio[bins] / n #calculate percentage of each bin
      #calculate mean
      sum_mean = 0
      for bin in dictio:
         sum_mean = sum_mean + bin * dictio[bin]
      mean = sum_mean
      #calculate sigma
      sum_sigma = 0
      for d in all_data:
         sum_sigma = sum_sigma + (d - mean)**2   
      sigma = np.sqrt(sum_sigma / amount_results)
      #set flags
      flags = {}
      if len(all_bins) == len(complete_bins):
         gapless =  True
      elif len(all_bins) < len(complete_bins):
         gapless = False
      else:
         print("ERROR")
         return -1, -1
      flags["gapless"] = gapless

      datapoint = {
         'prop': prop,
         'mean': mean,
         'sigma': sigma,
         'data': all_data,
         'bins': [all_bins, complete_bins],
         'dictio_bin_percent': dictio,
         'flags': flags
      }
      return amount_results, datapoint
   return amount_results, -1

def main():
   #list of all properties
   properties = html_parser()
   #open a json-file to save the data
   if os.path.exists("prop_mu_sig.json"):
      os.remove("prop_mu_sig.json")
   file = open("prop_mu_sig.json", "w")
   #open a txt-file to save the output
   if os.path.exists("log_json_gen.txt"):
      os.remove("log_json_gen.txt")
   output = open("log_json_gen.txt", "w")

   fail_props = []
   #interate through all props
   for prop in properties:
      if prop != "P31" and prop != "P279":
         print(prop)
         try:
            amount_results, datapoint = execute(prop)
            output.write("{}, {}\n".format(prop, amount_results))
            if datapoint != -1:
               json.dump(datapoint, file)
               file.write("\n")
         except Exception as e:
            print(e)
            fail_props.append(prop)
            output.write("{}, {}\n".format(prop, e))
         #if prop == "P16":
         #   break
   #retry the props which failed
   for fail in fail_props:
      try:
         amount_results, datapoint = execute(fail)
         output.write("{}, {}\n".format(fail, amount_results))
         if datapoint != -1:
            json.dump(datapoint, file)
            file.write("\n")
      except:
         continue
   output.write("Fail props: {}".format(fail_props))
   output.close()

if __name__ == '__main__':
    main()