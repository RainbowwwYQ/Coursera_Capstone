# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 13:33:52 2020

@author: yuqing
"""

from bs4 import BeautifulSoup
from urllib.request import urlopen
# import re
import pandas as pd
import urllib

def get_html(url):
    headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    global html
    html = urlopen(req).read().decode('ISO-8859-1')
    global soup
    soup = BeautifulSoup(html,'html.parser')

get_html("https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M")


# -------------------------------------------

# Part one: Data Scrapping and Pre-processing

# -------------------------------------------

# find the table first, go to the tbody section and find all labels called “tr"
content_extracted = soup.find("table")
content = content_extracted.tbody.find_all("tr")

res = []
for tr in content:
    
    td = tr.find_all("td")
    data = [tr.text for tr in td]
    
    # according to the requirement: 
    # only process the cells that have an assigned borough. 
    # Ignore cells with a borough that is Not assigned.
    if (data != []) and (data[1].strip() != "Not assigned"):
        
        # another requirement: 
        # if a cell has a borough but a Not assigned neighborhood
        # then the neighborhood will be the same as the borough
        if data[2].strip() == "Not assigned": 
            data[2] = data[1]
        
        res.append(data)

# Dataframe with 3 columns
df = pd.DataFrame(res, columns = ["PostalCode", "Borough", "Neighborhood"])
df.head()

# there are some "\n", which needs to be replaced
df["Neighborhood"] = df["Neighborhood"].str.replace("\n","")
df["Borough"] = df["Borough"].str.replace("\n","")
df["PostalCode"] = df["PostalCode"].str.replace("\n","")
df.head()
print("Shape: ", df.shape)

# we don't need to group the postcodes since it has been done by wiki itself!!!


# -------------
#  method two 
# -------------

# #reading table from wikipedia page
# Toronto_df = pd.read_html("https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M", header=0, attrs={"class":"wikitable sortable"})[0]
# Toronto_df.head()

# # lets drop Borough that has cells with 'Not assigned' values
# Not_assigned = Toronto_df[Toronto_df['Borough'] == 'Not assigned'].index
    
# # Delete these row indexes from dataFrame
# Toronto_df.drop(Not_assigned , inplace=True)

# #lets change cells that are having 'Not assigned' values in Neighborhood coloumn to match its corresponding Borough index
# Toronto_df.loc[Toronto_df['Neighbourhood'] == 'Not assigned', ['Neighbourhood']] = Toronto_df['Borough']

# #lets group Neighborhoods having the same postalcode
# Toronto_df = Toronto_df.groupby(['Postcode','Borough'])['Neighbourhood'].apply(', '.join).reset_index()

# ---------------
#  method three 
# ---------------

# source = requests.get('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M').text
# soup=BeautifulSoup(source,'lxml')
# print(soup.title)
# from IPython.display import display_html
# tab = str(soup.table)
# display_html(tab,raw=True)

# dfs = pd.read_html(tab)
# df=dfs[0]
# df.head()

# # Dropping the rows where Borough is 'Not assigned'
# df1 = df[df.Borough != 'Not assigned']

# # Combining the neighbourhoods with same Postalcode
# df2 = df1.groupby(['Postcode','Borough'], sort=False).agg(', '.join)
# df2.reset_index(inplace=True)

# # Replacing the name of the neighbourhoods which are 'Not assigned' with names of Borough
# df2['Neighbourhood'] = np.where(df2['Neighbourhood'] == 'Not assigned',df2['Borough'], df2['Neighbourhood'])

# -------------------------------------------

# part two: transfer addresses into lat/lon

# -------------------------------------------

# below it's the try to retrieve the data from geocoder, 
# however, there is no response for a long time. so choose to use the csv file

# import geocoder

# # initialize your variable to None
# lat_lng_coords = None

# # loop until you get the coordinates
# while(lat_lng_coords is None):
#   g = geocoder.google('{}, Toronto, Ontario'.format("M5G"))
#   lat_lng_coords = g.latlng

# latitude = lat_lng_coords[0]
# longitude = lat_lng_coords[1]

# import the csv file from online source
lat_lon = pd.read_csv('https://cocl.us/Geospatial_data')
lat_lon.head()

# merge two tables according to postcodes

df_toronto = pd.merge(df, lat_lon, how = "left", left_on = 'PostalCode', \
                      right_on = 'Postal Code')
df_toronto.drop("Postal Code", axis=1, inplace=True)
df_toronto.head()


# --------------------------------------------------

# part three: Explore and cluster the neighborhoods

# --------------------------------------------------

# get a general idea of how many boroughs and neighborhoods we have
print('The dataframe has {} boroughs and {} neighborhoods.'.format(
        len(df_toronto['Borough'].unique()),
        len(df_toronto['Neighborhood'].unique())
    )
)

# create a map of Toronto with neighborhoods 

from geopy.geocoders import Nominatim # convert an address into latitude and longitude values
import folium # map rendering library

address = "Toronto, ON"

geolocator = Nominatim(user_agent="toronto_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Toronto city are {}, {}.'.format(latitude, longitude))

# create map of Toronto using latitude and longitude values
map_toronto = folium.Map(location=[latitude, longitude], zoom_start=10)
map_toronto

#  add more attributes into this map
for lat, lng, borough, neighborhood in zip(
        df_toronto['Latitude'], 
        df_toronto['Longitude'], 
        df_toronto['Borough'], 
        df_toronto['Neighborhood']):
    label = '{}, {}'.format(neighborhood, borough)
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=0.7,
        parse_html=False).add_to(map_toronto)  

map_toronto

# using K-means clustering for all the neigbourhoods
from sklearn.cluster import KMeans

k = 5 # let's assume the number of clusters is 5
toronto_clustering = df_toronto.drop(['PostalCode','Borough','Neighborhood'],1)
kmeans = KMeans(n_clusters = k,random_state=0).fit(toronto_clustering)
kmeans.labels_[0:10]

# create a new dataframe that includes the clustering information
df_toronto.insert(0, 'Cluster Labels', kmeans.labels_)
df_toronto

# let's visualize the resulting clusters
import matplotlib.cm as cm
import matplotlib.colors as colors
import numpy as np

map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = np.arange(k)
ys = [i + x + (i*x)**2 for i in range(k)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# add markers to the map
markers_colors = []
for lat, lon, poi, cluster in zip(df_toronto['Latitude'], \
                                  df_toronto['Longitude'], \
                                  df_toronto['Neighborhood'], \
                                  df_toronto['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster-1],
        fill=True,
        fill_color=rainbow[cluster-1],
        fill_opacity=0.7).add_to(map_clusters)
       
map_clusters











