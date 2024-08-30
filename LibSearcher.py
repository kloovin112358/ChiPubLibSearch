
"""
Determines which books from an exported goodreads list are available at a specified branch of Chicago Public Library
"""

import requests
from bs4 import BeautifulSoup
import urllib
import pandas as pd

# this can be pulled from Goodreads from https://www.goodreads.com/review/import
# if you have additional books in your export besides those on your "Want to Read" shelf,
# you can add in additional logic below to filter out those entries
# or, you can just trim those out of your CSV manually
filename = 'goodreads_export.csv'

# built based on a URL for searching the Harold Washington library for books only
# in order to build a URL for your library branch, change the avlocation parameter
# in the URL to the specified branch (may have to URL-ify the name (ex: Harold Washington Library Center -> Harold%20Washington%20Library%20Center))
# in order to determine your branch's name in the system, go to CPL advanced search and run a test, which should show the actual string
URL_start = "https://chipublib.bibliocommons.com/v2/search?custom_edit=false&query=anywhere%3A("
URL_end = ")%20%20%20avlocation%3A%22Harold%20Washington%20Library%20Center%22%20formatcode%3A(BK%20)&searchType=bl&suppress=true"

floor_details_url_start = "https://gateway.bibliocommons.com/v2/libraries/chipublib/availability/"
floor_details_url_end = "?locale=en-US"

export_list = []

# if you only want to check out X books, might as well stop Python from searching all entries in the CSV file
stop_after_this_many_books = 10

datareader = pd.read_csv(filename)

# want to randomize the order of the file
# if you don't want this feature, because the priority of the books you want to read
# are set in the CSV file, reference the original datareader object instead of datareader_shuffled below
datareader_shuffled = datareader.sample(frac=1)

# adding this function adds on additional complexity that is not needed depended on the library
def getFloorOnLibraryBookIsOn(resultHTML):
    # this href link provides the reference ID we need, but the link provided is to an HTML page. We want the JSON version.
    og_CPL_availability_link = resultHTML.find('a', {'class': 'availability-link'}).attrs['href']
    book_ref_id = og_CPL_availability_link.split("availability/",1)[1]
    floor_details = requests.get(url = floor_details_url_start + book_ref_id + floor_details_url_end)
    floor_details_json = floor_details.json()
    
    # now we have to parse the JSON looking for the the 'collection' field within the correct branch
    for bookItem in floor_details_json['items'][0]['items']:
        if bookItem['branchName'] == "Harold Washington Library Center":
            return bookItem['collection']

    return "Floor Not Found"

for i, row in datareader_shuffled.iterrows():
    insert_into_query = urllib.parse.quote((row['Title'] + " " + row['Author']))
    r = requests.get(url = URL_start + insert_into_query + URL_end)
    resultHTML = BeautifulSoup(r.text, "html.parser")
    # we are just pulling the first book entry found in the system
    callNum = resultHTML.find('span', {'class': 'call-number'})
    if callNum is not None:
        # once we know a book has been found in the system, we want to pull which floor it is on
        # note that this may only be relevant for some branches - since I use Harold Washington, there are a lot of floors to search through
        bookFloor = getFloorOnLibraryBookIsOn(resultHTML)
        export_list.append(
            [resultHTML.find('span', {'class': 'title-content'}).text.strip(),
            resultHTML.find('a', {'class': 'author-link'}).text.strip(),
            callNum.text.strip(),
            bookFloor]
        )
    if len(export_list) == stop_after_this_many_books:
        break

# sort the list, coutesy of https://stackoverflow.com/a/20099713
export_list = sorted(export_list, key= lambda x: x[3], reverse=True)

if len(export_list) > 0:
    # printing code borrowed courtesy of https://stackoverflow.com/a/13214945
    s = [[str(e) for e in row] for row in export_list]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = '\t'.join('{{:{}}}'.format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    print ('\n'.join(table))
else:
    print("Sorry, none of your selected titles were available at your chosen Chicago Public Library branch.")

# note that this is a simple export format - I plan to just take a photo of the
# printed output. A more advanced version might create a Google Keep note or send an email to yourself