import requests
from xml.dom import minidom
from xml.etree import ElementTree as ET
import sqlite3 as sq
import json
from math import radians, cos, sin, asin, sqrt
import time
import webbrowser, os

try:
    import Queue as Q  # ver. < 3.0
except ImportError:
    import queue as Q
try:
    import gmplot  # ver. < 3.0
except :
	pass

def latlon(c,id):
	c.execute('SELECT * FROM coordinates WHERE id=?',(id,))
	l=c.fetchone()
	return l[1],l[2]

def haversine(lon1, lat1, lon2, lat2):#heuristic function h(n)
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. 
    return c * r *1000

def haversine_distance(c,id1,id2):
	a,b=latlon(c,id1)
	cc,d=latlon(c,id2)
	return haversine(float(b),float(a),float(d),float(cc))

def real_distance(c,id1,id2):#real distance g(n)
	a,b=latlon(c,id1)
	cc,d=latlon(c,id2)
	parameters={'origins':cc+','+d,'destinations':a+','+b,'key':'AIzaSyB7ihsepc6US8WxU4J3J52x2KPhOYcanKk'}
	url='https://maps.googleapis.com/maps/api/distancematrix/json?units=metric'
	while True:
		try:
			r=requests.get(url,params=parameters)
			break
		except requests.exceptions.RequestException as e:
		    print e
		    time.sleep(8)
	try :
		j=json.loads(r.text)
		distance=j['rows'][0]['elements'][0]['distance']['value']
		return distance
	except:
		print("api call failed")



def distances(c,id1,id2,destination):
	rd=real_distance(c,id1,id2)
	hd=haversine_distance(c,id2,destination)
	return hd,rd

def distances2(c,id1,id2,destination):
	rd=haversine_distance(c,id1,id2)
	hd=haversine_distance(c,id2,destination)
	return hd,rd

def A(N,matrix,dict2,c,source_id,destination_id):#A* algorithm
	source=source_id
	destination=destination_id
	par=[]
	dist=[]
	for i in range(N+1):
		par.append(0)
		dist.append(10000000000000000)
	q=Q.PriorityQueue()
	q.put((0,0,source))
	dist[source]=0
	while not q.empty():
		(f,g,id)=q.get()
		if id==destination:
			break
		#print(f,g,f-g,id,dict2[id])
		for child in matrix[id]:
			hd,rd=distances2(c,id,child,destination)
			if dist[child]>dist[id]+rd:
				dist[child]=dist[id]+rd#dist[child]=g(n) and hd+dist[child]=f(n)
				par[child]=id
				q.put((hd+dist[child],dist[child],child))
	if(par[destination]==0):
		print("destination not reached")
		return []
	ans=[]
	id=destination
	while id!=0:
		ans.insert(0,dict2[id])
		id=par[id]
	return ans#return the array of nodes visited in order i.e. route


conn = sq.connect("database.db")
conn.execute('drop table if exists coordinates')
sql='create table '+'coordinates'+'(id INT  primary_key,lat TEXT,long TEXT)'
conn.execute(sql)
cc=conn.cursor()
conn.commit()


#database creation and map creation
dict1={}
dict2={}
mydoc = minidom.parse('map.osm')
nodes=mydoc.getElementsByTagName('node')
c=1;
for elem in nodes:
	dict1[int(elem.attributes['id'].value)]=c
	dict2[c]=int(elem.attributes['id'].value)
	cc.execute('INSERT INTO coordinates (id,lat,long) VALUES(?,?,?)',(c,elem.attributes['lat'].value,elem.attributes['lon'].value))
	c=c+1
conn.commit()
conn.close()


#graph creation
conn = sq.connect("database.db")
matrix=[]
for i in range(c):
	matrix.append([])
N=c#number of nodes


c=conn.cursor()


#graph creation
rootElement = ET.parse("map.osm").getroot()
for subsub in rootElement:
	if subsub.tag=='way':
		ch=False
		for sub in subsub:
			if sub.tag=='tag':
				if sub.attrib['k']=='highway':
					ch=True
		if ch:
			prev=-1
			first=-1
			for sub in subsub:
				if sub.tag=='nd':
					v=(int)(sub.attrib['ref'])
					v=dict1[v]
					if prev!=-1:
						matrix[prev].append(v)
						matrix[v].append(prev)
					else :
						first=v
					prev=v


#A* algorithm
source_id=2684789173
#destination_id=2791955415
#destination_id=2684820164 #use 
destination_id=4193132280
a=A(N,matrix,dict2,c,dict1[source_id],dict1[destination_id])


lat=[]
lon=[]
if len(a)!=0:
	print("the route:")
	print("node,latitude,longitude")
	for elem in a:
		la,lo=latlon(c,dict1[elem])
		lat.append(float(la))
		lon.append(float(lo))
		print(elem,float(la),float(lo))

	conn.close()

	#draw the graph with the help of gmplot
	try:
		gmap = gmplot.GoogleMapPlotter(lat[0],lon[0],16)
		gmap.plot(lat, lon, 'orange' , edge_width = 10)
		gmap.scatter(lat, lon, 'red', size =20, marker = True)
		gmap.draw('mapdisplay.html')
		webbrowser.open('file://' + os.path.realpath('mapdisplay.html'))
	except:
		pass
