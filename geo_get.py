import pandas as pd
from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.error import HTTPError
import unicodedata
import LatLon23
import requests
import json
import calendar
import time
from PIL import Image
from unidecode import unidecode
import re

rows_list = []
arr_img = []

for i in range(380, 11400):  # 11400
    print('getting: ', i)
    url = "http://jaskiniepolski.pgi.gov.pl/Details/Information/" + str(i)
    try:
        page = urlopen(url)
        soup = BeautifulSoup(page.read().decode('utf-8', 'ignore'), "html.parser")
        all_tables = soup.find_all('table')
        if len(all_tables) != 1:
            print(i, " len(all_tables): ", len(all_tables))
            continue
    except HTTPError as e:
        print(i, e)
        continue

    d = dict()

    for row in all_tables[0].find_all("tr"):
        columns = row.find_all("td")
        name = ' '.join(columns[0].get_text().strip().split())
        val = ''
        if name == 'Grafika, zdjęcia':
            a_tab = columns[1].find_all("a")

            for a in a_tab:
                key = a.get_text().strip()
                img_num = a.get('onclick').replace('showImageInfo(', '').replace(')', '')
                # time.sleep(1)
                r = requests.post("http://jaskiniepolski.pgi.gov.pl/Details/ImageInformation", data={'id': img_num})
                if r.status_code == 200:
                    j_img = json.loads(r.text)
                    j_img['index'] = i
                    arr_img.append(j_img)
                    # time.sleep(1)
                else:
                    print(r)
                url = "http://jaskiniepolski.pgi.gov.pl/Details/RenderImage?id={0}&zoom=5&ifGet=false&date={1}".format(
                    img_num, calendar.timegm(time.gmtime()))
                r = requests.get(url)
                if r.status_code == 200:
                    file_name = "img/{0}_{1}_{2}_{3}.jpg".format(i, img_num, j_img['grafika_nazwa'].replace(' ', '_'),
                                                                 re.sub(r'\s\(.*\)', '', unidecode(d['Nazwa'])).replace(
                                                                     ' ', '_').replace('"', '_'))
                    with open(file_name, 'wb') as f:  # TODO add replace
                        f.write(r.content)
                        im = Image.open(file_name)
                        assert (j_img['maxWidth'], j_img['maxHeight']) == im.size
                else:
                    print(r)
                d['image'] = d[key] if key in d.keys() else '' + img_num + ';'
                d['image_file'] = d['image_file'] if 'image_file' in d.keys() else '' + file_name + ';'
        elif name == 'Właściciel terenu':
            val = columns[1].get_text().strip()
            val = re.sub('  +', ' ', val)
            d[name] = val.replace('\r\n| ', ';')
        elif name == 'Długość [m] w tym szacowane [m]':
            val = columns[1].get_text().strip()
            val = re.sub('  +', ' ', val)
            d[name] = val.replace('\r\n \n\r\n ', ';')
        elif name == 'Współrzędne WGS84':
            str_gps = columns[1].get_text().strip()
            # from https://github.com/hickeroar/LatLon23
            str_gps_arr = str_gps.replace(',', '.').split('. ')
            d['D lat'] = ''
            d['D lon'] = ''
            d['DM lat'] = ''
            d['DM lon'] = ''
            d['DMS lat'] = ''
            d['DMS lon'] = ''
            if len(str_gps_arr) == 2:
                caveLatLon = LatLon23.string2latlon(str_gps_arr[1][2:], str_gps_arr[0][2:], 'd%°%m%′%S%″')
                d['D lat'] = caveLatLon.to_string('D% %H')[0]
                d['D lon'] = caveLatLon.to_string('D% %H')[1]
                d['DM lat'] = caveLatLon.to_string('d% %M% %H')[0]
                d['DM lon'] = caveLatLon.to_string('d% %M% %H')[1]
                d['DMS lat'] = caveLatLon.to_string('d% %m% %S% %H')[0]
                d['DMS lon'] = caveLatLon.to_string('d% %m% %S% %H')[1]
        else:
            val = columns[1].get_text().strip()
            val = re.sub('  +', ' ', val)
            d[name.strip()] = unicodedata.normalize("NFKD", val)
    d['index'] = i
    # temp_df = pd.DataFrame(d, index = [i])
    rows_list.append(d)
    # time.sleep(1)

df = pd.DataFrame(rows_list)
df_img = pd.DataFrame(arr_img)

df.set_index('index')
# TODO check numners of results with search page

df.to_pickle("jaskinie_20180716.pickle")
df_img.to_pickle("img_20180716.pickle")

df.to_csv('jaskinie_20180716.csv')
df_img.to_csv('img_20180716.csv')

# TODO http://potrace.sourceforge.net/
# TODO https://pypi.org/project/pypotrace/
