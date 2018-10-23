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
import time
import sys
import os

max_rec = 0x100000
sys.setrecursionlimit(max_rec)

sleep_time = 0
date_name = '181023'
img_folder = '{0}_img'.format(date_name)

if not os.path.exists(img_folder):
    os.makedirs(img_folder)

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
                time.sleep(sleep_time)
                r = requests.post("http://jaskiniepolski.pgi.gov.pl/Details/ImageInformation", data={'id': img_num})
                if r.status_code == 200:
                    j_img = json.loads(r.text)
                    j_img['index'] = i
                    arr_img.append(j_img)
                    time.sleep(sleep_time)
                else:
                    print(r)
                url = "http://jaskiniepolski.pgi.gov.pl/Details/RenderImage?id={0}&zoom=5&ifGet=false&date={1}".format(
                    img_num, calendar.timegm(time.gmtime()))
                r = requests.get(url)
                if r.status_code == 200:
                    file_name = "{0}/{1}_{2}_{3}_{4}.jpg".format(img_folder, i, img_num,
                                                                 j_img['grafika_nazwa'].replace(' ', '_'),
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
            if columns[1].find('style') is not None:
                columns[1].style.extract()
            val = columns[1].get_text().strip()
            val = re.sub('  +', ' ', val)
            d[name.strip()] = val  # unicodedata.normalize("NFKD", val)
            d[name.strip() + '_ORG_HTML'] = columns[1]
            # print(columns[1])
    d['index'] = i
    rows_list.append(d)
    time.sleep(sleep_time)

df = pd.DataFrame(rows_list)
df_img = pd.DataFrame(arr_img)

df.set_index('index')

df['Deniwelacja [m]'] = pd.to_numeric(df['Deniwelacja [m]'].str.replace(',', '.'))
df['Głębokość [m]'] = pd.to_numeric(df['Głębokość [m]'].str.replace(',', '.'))
df['Wysokość względna [m]'] = pd.to_numeric(df['Wysokość względna [m]'].str.replace(',', '.'))
df['Wysokość bezwzględna [m n.p.m.]'] = pd.to_numeric(df['Wysokość bezwzględna [m n.p.m.]'].str.replace(',', '.'))
df['Przewyższenie [m]'] = pd.to_numeric(df['Przewyższenie [m]'].str.replace(',', '.'))
df['Rozciągłość horyzontalna [m]'] = pd.to_numeric(df['Rozciągłość horyzontalna [m]'].str.replace(',', '.'))

df['Zniszczona, niedostępna lub nieodnaleziona'] = df['Zniszczona, niedostępna lub nieodnaleziona'].astype('category')
df['Ekspozycja otworu'] = df['Ekspozycja otworu'].astype('category')
df['Województwo'] = df['Województwo'].astype('category')

# TODO something wrong with this
# df['Długość [m] w tym szacowane [m]'] =  df['Długość [m] w tym szacowane [m]'].str.replace(',', '.')
# df['Długość']=pd.to_numeric(df['Długość [m] w tym szacowane [m]'].str.split(';', expand=True)[0])
# df['Długość szacowana']=pd.to_numeric(df['Długość [m] w tym szacowane [m]'].str.split(';', expand=True)[1])
# df=df.drop(['Długość [m] w tym szacowane [m]'], axis=1)

# TODO check numbers of results with search page

df.to_pickle('jaskinie_{0}.pickle'.format(date_name))
df_img.to_pickle('img_{0}.pickle'.format(date_name))

df.to_csv('jaskinie_{0}.csv'.format(date_name))
df_img.to_csv('img_{0}.csv'.format(date_name))

writer = pd.ExcelWriter('{0}.xlsx'.format(date_name))
df.to_excel(writer, 'jaskinie')
df_img.to_excel(writer, 'img')
writer.save()

# TODO http://potrace.sourceforge.net/
# TODO https://pypi.org/project/pypotrace/
