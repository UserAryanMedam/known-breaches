import subprocess
import sys
import requests
import json
import csv
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

"""
Scrapes in the indexed/available datasets from several data aggregators/indexers. Currently supports Dehashed, Leak-Lookup, HaveIBeenPwned
"""

def add_source(breaches, source):
    """
    Adds a source field to a list of breaches.
    """
    for breach in breaches:
        breach["source"] = source
    return breaches

def clean_json(breaches):
    """
    Cleans an array of json objects by stripping any key/value pairs where the key is not in the whitelist.
    """
    whitelist = ["dump_name","breach_date","record_count","info","index_date","description","source"]
    clean_breaches = []
    for breach in breaches:
        clean_breach = {}
        for key in breach.keys():
            if key in whitelist:
                clean_breach[key] = breach[key]
        clean_breaches.append(clean_breach)
    return clean_breaches

def remove_non_digits(string):
    """
    Removes non-digits from a string.
    """
    return ''.join(filter(lambda x: x.isdigit(), string))

def generate_requests_session():
    """
    Generates a requests session.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
    })
    return session

def scrape_leaklookup(session=generate_requests_session()):
    """
    Scrapes the Leak-Lookup dataset.
    """
    breaches = []
    url = "https://leak-lookup.com/breaches"
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        data_table = soup.find('table', {'id': 'datatables-indexed-breaches'})
        for entry in data_table.find('tbody').find_all('tr'):
            """
            Example <tr>
            <tr>
                <td>astropid.com</td>
                <td class="d-xl-table-cell">5,789</td>
                <td class="d-xl-table-cell">2017-02-20</td>
                <td class="table-action text-center">
                    <div class="dropdown position-relative">
                        <a href="#" data-bs-toggle="dropdown" data-bs-display="static">
                            <i class="align-middle" data-feather="more-horizontal"></i>
                        </a>

                        <div class="dropdown-menu dropdown-menu-end">
                            <a id="astropid-com" class="dropdown-item" data-bs-toggle="modal" data-id="1" data-bs-target="#breachModal">Information</a>
                        </div>
                    </div>
                </td>
            </tr>
            """
            tds = entry.find_all('td')
            dump_name = tds[0].text.strip()
            record_count = remove_non_digits(tds[1].text.replace(",","").strip())
            # YYYY-MM-DD
            date = tds[2].text.strip()
            breaches.append({"dump_name": dump_name, "record_count": record_count, "index_date": date, "source": "leaklookup"})
        return breaches
    else:
        return None

def scrape_hibp(session=generate_requests_session()):
    """
    Scrapes the HaveIBeenPwned dataset.
    """
    breaches = []
    url = "https://haveibeenpwned.com/PwnedWebsites"
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        data_table = soup.find_all('div', {'class': 'row'})
        for entry in data_table:
            """
            Example entry
            <div class="container">
            <hr /><a id="000webhost"></a>
            <div class="row">
            <div class="col-sm-2">
            <img class="pwnLogo large" src="/Content/Images/PwnedLogos/000webhost.png" alt="000webhost logo" />
            </div>
            <div class="col-sm-10">
            <h3>
            000webhost
            </h3>
            <p>In approximately March 2015, the free web hosting provider <a href="https://www.troyhunt.com/2015/10/breaches-traders-plain-text-passwords.html" target="_blank" rel="noopener">000webhost suffered a major data breach</a> that exposed almost 15 million customer records. The data was sold and traded before 000webhost was alerted in October. The breach included names, email addresses and plain text passwords.</p>
            <p>
            <strong>Breach date:</strong> 1 March 2015<br />
            <strong>Date added to HIBP:</strong> 26 October 2015<br />
            <strong>Compromised accounts:</strong> 14,936,670<br />
            <strong>Compromised data:</strong> Email addresses, IP addresses, Names, Passwords<br />
            <a href="#000webhost">Permalink</a>
            </p>
            </div>
            </div>
            """
            if "Breach date:" in entry.text:
                # valid entry
                dump_name = entry.find('h3').text.strip()
                breach_date = entry.find_all('p')[1].text.splitlines()[1].split(":")[1].strip()
                index_date = entry.find_all('p')[1].text.splitlines()[2].split(":")[1].strip()
                record_count = remove_non_digits(entry.find_all('p')[1].text.splitlines()[3].split(":")[1].strip())
                description = entry.find_all('p')[0].text.strip()
                info = entry.find_all('p')[1].text.splitlines()[4].split(":")[1].strip()
                breaches.append({"dump_name": dump_name, "record_count": record_count, "breach_date": breach_date, "index_date": index_date, "description": description, "info": info, "source": "hibp"})
        return breaches
    else:
        return None


def scrape_dehashed(session=generate_requests_session()):
    """
    Scrapes the Dehashed dataset index.

    """
    breaches = []
    url = "https://webcache.googleusercontent.com/search?q=cache:https://dehashed.com/data"
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        data_table = soup.find('table', {'class': 'table table-hover'})
        for entry in data_table.find('tbody').find_all('tr'):
            """
            Example <tr>
            <tr>
            <td class="align-middle">2paclegacyboard.net</td>
            <td class="align-middle">
            <abbr class="bs-tooltip" data-placement="top" title='-'>Hover Here</abbr>
            <p></p>
            </td>
            <td class="align-middle"><span class="text-nowrap">N/A</span></td>
            <td class="align-middle"><span class="text-nowrap">1061</span></td>
            <td class="align-middle"><abbr class="bs-tooltip" data-placement="top" title='N/A'>Hover Here</abbr></td>
            </tr>
            """
            tds = entry.find_all('td')
            dump_name = tds[0].text.strip()
            breach_date = tds[2].find('span').text.strip()
            record_count = remove_non_digits(tds[3].find('span').text.replace(",","").strip())
            info = tds[4].find('abbr')['title'].strip()
            breaches.append({"dump_name": dump_name, "breach_date": breach_date, "record_count": record_count, "info": info, "source": "dehashed"})
        return breaches
    else:
        return None
    
def extract_base_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    base_domain = domain.split('.')[-2]  # Extract the second-to-last part of the domain
    return base_domain
    
def stats(breaches):
    total_recs = 0
    max_recs = 0
    max_recs_source = ""
    seen_entries = set()


    for element in breaches:
        current_recs = (element).get('record_count')
        
        dump_name = element.get('dump_name')
        breach_date = element.get('breach_date')
            
            # Check for duplicates
        if (dump_name, breach_date) in seen_entries:
            # print(f"Duplicate detected: {dump_name}, {breach_date}. Skipping.")
            continue

        seen_entries.add((dump_name, breach_date))
        
        try:
            current_recs = int(current_recs)
            total_recs += (current_recs)
            if (current_recs > max_recs):
                max_recs = current_recs
                max_recs_source= (element).get('dump_name')
        except:
           pass

        


    # sums total records leaked

    return [total_recs, max_recs, max_recs_source]

# path for history json /Users/venkateswarlumedam/Downloads/Takeout-3/Chrome/History.json

def history_json_to_sites(path):
    
    base_url_set = set([])

    with open(path, 'r') as file:
        history_data = json.load(file)
        for element in history_data["Browser History"]:

            base_url_set.add(extract_base_domain(str(element["url"])))
    return base_url_set
    

if __name__ == "__main__":
    # scrape datasets from dehashed
    history = history_json_to_sites("/Users/venkateswarlumedam/Downloads/Takeout-3/Chrome/History.json")
    # replace this with your own Takeout/Chrome/History.json path 

    breaches = []
    print("Scraping Dehashed.com")
    try:
        dehashed_result = scrape_dehashed()
        if dehashed_result:
            breaches += dehashed_result
            print("Saving results to file")
            with open("datasets/dehashed.json", "w") as f:
                json.dump(dehashed_result, f)
            with open("datasets/dehashed.csv", "w") as f:
                writer = csv.DictWriter(f, fieldnames=["dump_name","breach_date","record_count","info","source"])
                writer.writeheader()
                writer.writerows(dehashed_result)
            print("Successfully scraped {} breaches from Dehashed.com".format(len(dehashed_result)))
        else:
            print("Scraping dehashed failed")
    except:
        print("Error occured while scraping dehashed")
    # scrape datasets from HaveIBeenPwned

    print("Scraping HaveIBeenPwned.com")
    try:
        hibp_result = scrape_hibp()
        if hibp_result:
            breaches += hibp_result
            print("Saving results to file")    
            with open("datasets/hibp.json", "w") as f:
                json.dump(hibp_result, f)
            with open("datasets/hibp.csv", "w") as f:
                writer = csv.DictWriter(f, fieldnames=["dump_name","breach_date","record_count","info","index_date","description","source"])
                writer.writeheader()
                writer.writerows(hibp_result)
        else:
            print("Scraping of HIBP failed")
    except Exception as e:
        print(str(e))
        print("Error occured while scraiping hibp")
    print("Successfully scraped {} breaches from HaveIBeenPwned.com".format(len(hibp_result)))
    
    # scrape datasets from LeakLookup
    print("Scraping Leak-Lookup.com")
    try:
        ll_result = scrape_leaklookup()
        breaches += ll_result
        if ll_result:
            print("Saving results to file")
            with open("datasets/leaklookup.json", "w") as f:
                json.dump(ll_result, f)
            with open("datasets/leaklookup.csv", "w") as f:
                #breaches.append({"dump_name": dump_name, "record_count": record_count, "index_date": date, "source": "leaklookup"})

                writer = csv.DictWriter(f, fieldnames=["dump_name","record_count","index_date","source"])
                writer.writeheader()
                writer.writerows(ll_result)
        else:
            print("Scraping of leak-lookup failed")
    except:
        print("Error occured while scraping Leak-Lookup")
    print("Successfully scraped {} breaches from Leak-Lookup.com".format(len(ll_result)))

    # load static datasets
    # loop through each JSON file in the datasets/ directory
    ignore_files = ["combined.json","hibp.com","dehashed.json","leaklookup.json","HackNotice.com.json"] # HackNotice excluded to reduce noise/size
    for file in os.listdir("datasets/"):
        if file.endswith(".json") and file not in ignore_files:
            print("Loading {}".format(file))
            try:
                with open("datasets/{}".format(file), "r") as f:
                    json_data = json.loads(f.read())
                    for entry in json_data:
                        entry["source"] = file.replace(".json","")
                    breaches += json_data
                    print("Extracted {} breaches from {}".format(len(json_data), file))
            except:
                print("Error occured while loading {}".format(file))

    # save combined results 
    breaches = clean_json(breaches)

    print("Saving combined results to file")
    with open("datasets/combined.json", "w") as f:
        f.write(json.dumps(breaches, separators=(',', ':')))

    
    statistics = stats(breaches)

    
    breached_sites = set([])
    for breach in breaches:
        breached_sites.add(breach['dump_name']) # add breached sites to the set as a list
    
    breaches_that_affect_you = []
    for breach in breached_sites:
        if (breach in history):
            breaches_that_affect_you.append(breach)
    subprocess.call(['touch', "breaches_that_affect_you.txt"])
    os.remove("breaches_that_affect_you.txt")
    print(breaches_that_affect_you)
    
    subprocess.call(['touch', "breaches_that_affect_you.txt"])

    # with open("breaches_that_affect_you.csv", "w", newline="") as CSVFILE:
    #     writer = csv.writer(CSVFILE, delimiter=',')
    #     writer.writerows(breaches_that_affect_you)
    FILE = open("breaches_that_affect_you.txt", "a")
    for element in breaches_that_affect_you:

        FILE.write(element)
        FILE.write("\n")
    FILE.close()

    # writes the shared breaches to file
    


    print(f" total records leaked: {statistics[0]} \n greatest number of records leaked from one source: {statistics[1]} \n source of that leak: {statistics[2]}")
    subprocess.call(["python3", "-m", "http.server", "8080"])
    print("Done :)")
