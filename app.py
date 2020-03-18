
from bs4 import BeautifulSoup as bs
import requests
import time
import urllib
import os
import pandas as pd
from flask import Flask, request, render_template
from flask_cors import CORS,cross_origin
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

app = Flask(__name__)

IMG_FOLDER = os.path.join('static', 'images')
CSV_FOLDER = os.path.join('static', 'CSVs')

# config environment variables
app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER

# source = requests.get('http://flipkart.com').text
# soup = bs(source, 'lxml')

# bd = soup.body.prettify()

class DataCollection(object):
	"""docstring for DataCollection"""
	def __init__(self):
		self.data = {
		"Product" : list(),
		"Name" : list(),
		"Price (INR)": list(),
		"Rating": list(), 
		"Comment Heading": list(), 
		"Comment": list(),
		"link" : list()
		}

	def get_html(slef,base_url=None,search_item=None):

		search_url = f"{base_url}/search?q={search_item}"
		with urllib.request.urlopen(search_url) as url:
			page = url.read()
		return bs(page,'html.parser')

	def get_product_name_links(self,base_url,bigboxes):
		temp = []
		for box in bigboxes:
			try:
				temp.append((box.div.div.div.a.img['alt'],
					base_url + box.div.div.div.a["href"]))
			except:
				pass

		return temp

	def get_prod_HTML(self, productLink=None):

		prod_page = requests.get(productLink)
		return bs(prod_page.text, "html.parser")

	def get_data_dict(self):
		return self.data

	def save_as_dataframe(self, dataframe, fileName=None):
		'''
		it saves the dictionary dataframe as csv by given filename inside
		the CSVs folder and returns the final path of saved csv
		'''
		# save the CSV file to CSVs folder
		csv_path = os.path.join(app.config['CSV_FOLDER'], fileName)
		fileExtension = '.csv'
		final_path = f"{csv_path}{fileExtension}"
		# clean previous files -
		CleanCache(directory=app.config['CSV_FOLDER'])
		# save new csv to the csv folder
		dataframe.to_csv(final_path, index=None)
		print("File saved successfully!!")
		return final_path

	def save_wordcloud_image(self, dataframe=None, img_filename=None):
		
		txt = dataframe["Comment"].values
		# generate the wordcloud
		wc = WordCloud(width=800, height=400, background_color='black', stopwords=STOPWORDS).generate(str(txt))

		plt.figure(figsize=(20,10), facecolor='k', edgecolor='k')
		plt.imshow(wc, interpolation='bicubic') 
		plt.axis('off')
		plt.tight_layout()
		# create path to save wc image
		image_path = os.path.join(app.config['IMG_FOLDER'], img_filename + '.png')
		# Clean previous image from the given path
		CleanCache(directory=app.config['IMG_FOLDER'])
		# save the image file to the image path
		plt.savefig(image_path)
		plt.close()
		print("saved wc")

	def get_final_data(self, commentbox=None, prodName=None, prod_price=None, prod_link=None):
		'''
		this will append data gathered from comment box into data dictionary
		'''
		# append product name
		self.data["Product"].append(prodName)
		self.data["link"].append(prod_link)
		self.data["Price (INR)"].append(prod_price)
		try:
			# append Name of customer if exists else append default
			self.data["Name"].append(commentbox.div.div.\
				find_all('p', {'class': '_3LYOAd _3sxSiS'})[0].text)
		except:
			self.data["Name"].append('No Name')

		try:
			# append Rating by customer if exists else append default
			self.data["Rating"].append(commentbox.div.div.div.div.text)
		except:
			self.data["Rating"].append('No Rating')

		try:
			# append Heading of comment by customer if exists else append default
			self.data["Comment Heading"].append(commentbox.div.div.div.p.text)
		except:
			self.data["Comment Heading"].append('No Comment Heading')

		try:
			# append comments of customer if exists else append default
			comtag = commentbox.div.div.find_all('div', {'class': ''})
			self.data["Comment"].append(comtag[0].div.text)
		except:
			self.data["Comment"].append('')

class CleanCache:
	
	def __init__(self, directory=None):
		self.clean_path = directory
		# only proceed if directory is not empty
		if os.listdir(self.clean_path) != list():
			# iterate over the files and remove each file
			files = os.listdir(self.clean_path)
			for fileName in files:
				print(fileName)
				os.remove(os.path.join(self.clean_path,fileName))
		print("cleaned!")



@app.route('/',methods=['GET'])  
@cross_origin()
def homePage():
	return render_template("index.html")

# route to display the review page
@app.route('/review', methods=("POST", "GET"))
@cross_origin()
def index():
	if request.method=='POST':
		try:
			base_url = 'https://www.flipkart.com'
			search_item = request.form['content']
			search_item = search_item.replace(" ","+")
			print("Processing.......")
			start = time.perf_counter()

			get_data = DataCollection()

			flipkart_html = get_data.get_html(base_url,search_item)


			bigboxes = flipkart_html.find_all("div", {"class" : "bhgxx2 col-12-12"})

			product_name_links = get_data.get_product_name_links(base_url,bigboxes)

			for prodName, product_link in product_name_links[:4]:
				for prod_html in get_data.get_prod_HTML(product_link):
					try:
						comment_boxes = prod_html.find_all('div', {'class': '_3nrCtb'})

						prod_price = prod_html.find_all('div', {"class": "_1vC4OE _3qQ9m1"})[0].text
						prod_price = float((prod_price.replace("₹", "")).replace(",", ""))
						for commentbox in comment_boxes:
							get_data.get_final_data(commentbox, prodName, prod_price, product_link)
					except:
						pass


			df = pd.DataFrame(get_data.get_data_dict())
			x = get_data.get_data_dict()

			download_path = get_data.save_as_dataframe(df, fileName=search_item.replace("+", "_"))
			get_data.save_wordcloud_image(df, 
			img_filename=search_item.replace("+", "_"))
			finish = time.perf_counter()
			print(f"program finished with and timelapsed: {finish - start} second(s)")
			
			return render_template('review.html',
				dic = x,
				df = df,
			tables=[df.to_html(classes='data')], # pass the df as html 
			titles=df.columns.values, # pass headers of each cols
			search_string = search_item, # pass the search string
			download_csv=download_path # pass the download path for csv
			)

		except Exception as e:
			print(e)
			# return 404 page if error occurs 
			return render_template("review.html")


	else:
		# return index page if home is pressed or for the first run
		return render_template("index.html")



@app.route('/show')
@cross_origin()
def show_wordcloud():
	img_file = os.listdir(app.config['IMG_FOLDER'])[0]
	full_filename = os.path.join(app.config['IMG_FOLDER'], img_file)
	return render_template("show_wc.html", user_image = full_filename)





if __name__ == '__main__':
	app.run(debug=True)


