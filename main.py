import requests
import re
import random
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os


NUMBER_OF_MATCHES = 5


# Function to create the directory that will contain the exported files
def create_export_directories(subdomain):
    """
    Create directories for exporting files.

    Parameters:
    - subdomain (str): The subdomain for the dApp.

    Returns:
    - str: Path to the created subdomain directory.
    """

    exports_directory = "exports"
    subdomain_directory = os.path.join(exports_directory, subdomain)
    os.makedirs(subdomain_directory, exist_ok=True)
    return subdomain_directory


# Function to export the ABI JSON to a file
def export_abi_json(abi_json, name_field, subdomain_directory):
    """
    Export the ABI JSON to a file.

    Parameters:
    - abi_json (dict): The ABI JSON data.
    - name_field (str): The name for the ABI.
    - subdomain_directory (str): Directory to save the ABI file.

    Returns:
    - str: Path to the saved ABI JSON file.
    """
    # Creating a filename based on the "name" field, ensuring uniqueness
    filename_base = name_field.replace(" ", "_")
    filename = filename_base + ".json"
    file_path = os.path.join(subdomain_directory, filename)
    unique_path = file_path
    os.path.join(subdomain_directory, f"{filename_base}.json")

    # Writing the ABI JSON to the file
    with open(unique_path, 'w') as file:
        json.dump(abi_json, file, indent=4)

    return unique_path


# Function to export the relationship dictionary to a JSON file
def export_relationship_dict(relationship_dict, subdomain_directory):
    """
    Export the relationship dictionary to a JSON file.

    Parameters:
    - relationship_dict (dict): Dictionary containing relationships between ABIs and contract addresses.
    - subdomain_directory (str): Directory to save the relationship JSON file.

    Returns:
    - str: Path to the saved relationship JSON file.
    """
    # Define the path for the relationship JSON file within the subdomain directory
    relationship_file_path = os.path.join(subdomain_directory, "relationship.json")

    # Open the file in write mode and use json.dump to write the dictionary
    with open(relationship_file_path, 'w') as file:
        json.dump(relationship_dict, file, indent=4)

    return relationship_file_path


# Function to modify the relationship JSON that indicates on which Smart Contract address corresponds with which ABI JSON
def track_sc_abi_relationship(sc_address, abi_json_path, relationship_dict):
    """
    Modifies the relationship JSON to indicate which Smart Contract address corresponds with which ABI JSON.

    Parameters:
    - sc_address (str): The Smart Contract address.
    - abi_json_path (str): Path to the ABI JSON file.
    - relationship_dict (dict): Dictionary to be updated with the relationship.

    Returns:
    - None
    """
    relationship_dict[sc_address] = abi_json_path


# Function to download a JavaScript file from the given URL
def download_js_file(url):
    response = requests.get(url)
    return response.text


# Function to find "buildInfo" (with or without quotes) in the JS code
# and locate the nearest opening brace "{" before "buildInfo"
def find_buildinfo_and_nearest_opening_brace(js_code):
    """
    Finds "buildInfo" (with or without quotes) in the JS code and locates the nearest opening brace "{" before "buildInfo".

    Parameters:
    - js_code (str): JavaScript code to search within.

    Returns:
    - List[Tuple[int, int]]: List of tuples containing the indices of the opening brace and "buildInfo".
    """
    index = 0
    occurrences = []

    while True:
        # Finding the index of "buildInfo" with quotes
        build_info_index = js_code.find('"buildInfo"', index)
        # Finding the index of "buildInfo" without quotes if not found with quotes
        if build_info_index == -1:
            build_info_index = js_code.find('buildInfo', index)

        if build_info_index == -1:
            break

        # Finding the opening brace that contains the JSON-like structure
        open_brace_index = js_code.rfind('{', 0, build_info_index)
        if open_brace_index != -1:
            occurrences.append((open_brace_index, build_info_index))

        # Updating the index for the next iteration
        index = build_info_index + 1

    return occurrences


# Function to extract the content between the matching opening and closing braces, considering nested braces
def extract_matching_braces_content(js_code, start_index):
    """
    Extracts content between the matching opening and closing braces, considering nested braces.

    Parameters:
    - js_code (str): JavaScript code to extract content from.
    - start_index (int): Index to start the extraction from.

    Returns:
    - str: Extracted content between matching braces.
    """
    open_brace_count = 0
    content = ""
    for i in range(start_index, len(js_code)):
        char = js_code[i]
        content += char
        if char == '{':
            open_brace_count += 1
        elif char == '}':
            open_brace_count -= 1
            if open_brace_count == 0:
                return content
    return None


# Function to repair JSON-like string (version 3)
def repair_json(s):
    """
    Repairs a JSON-like string by adding necessary formatting.

    Parameters:
    - s (str): The JSON-like string to be repaired.

    Returns:
    - str: Repaired JSON-like string.
    """
    # Adding quotes around keys
    s = re.sub(r'(\b[a-zA-Z_]\w*\b)(?=\s*[:])', r'"\1"', s)
    # Replacing single quotes with double quotes
    s = s.replace("'", '"')
    # Escaping any unescaped backslashes
    s = s.replace("\\", "\\\\")
    # Replacing !0 with true and !1 with false
    s = s.replace('!0', 'true')
    s = s.replace('!1', 'false')
    return s


# Function to extract the full JSON object from a given text starting at a specific index
def extract_full_json(text, start_index):
    """
    Extracts the full JSON object from a given text starting at a specific index.

    Parameters:
    - text (str): Text from which to extract the JSON.
    - start_index (int): Index to start the extraction from.

    Returns:
    - str: Extracted JSON string.
    """
    brace_count = 0
    for i in range(start_index, len(text)):
        char = text[i]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_index = i + 1
                return text[start_index:end_index]


# Function to extract smart contract addresses from the given JavaScript code
def extract_addresses(js_code):
    """
    Extracts smart contract addresses from the given JavaScript code.

    Parameters:
    - js_code (str): JavaScript code from which to extract addresses.

    Returns:
    - List[str]: List of extracted smart contract addresses.
    """
    sc_address_pattern = re.compile(r'\berd1qqqqqqqqq[0-9a-zA-Z]+\b')
    sc_address_matches = sc_address_pattern.findall(js_code)
    return [address for address in sc_address_matches if
            "erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqq" not in address]


# Function to get active addresses by querying Elasticsearch
def get_active_addresses(addresses):
    """
    Queries Elasticsearch to get active addresses.

    Parameters:
    - addresses (List[str]): List of addresses to query for.

    Returns:
    - list[str]: list of active addresses on the Mainnet.
    """
    # Elasticsearch query URL
    query_url = 'https://index.multiversx.com/accounts/_search'

    # Elasticsearch query body
    query_body = {
        "_source": False,
        "query": {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "address": addresses
                        }
                    }
                ]
            }
        },
        "size": 10000
    }

    # Performing the query
    response = requests.post(query_url, json=query_body)
    response_data = response.json()

    # Extracting the active addresses from the response
    active_addresses = [hit['_id'] for hit in response_data['hits']['hits']]

    return active_addresses


# Function to query a specific function of a smart contract
def query_function(sc_address, func_name):
    """
    Queries a specific function of a smart contract.

    Parameters:
    - sc_address (str): Smart contract address to query.
    - func_name (str): Name of the function to query.

    Returns:
    - dict: Response from the query.
    """
    query_url = 'https://gateway.multiversx.com/vm-values/query'
    post_body = {
        "scAddress": sc_address,
        "funcName": func_name,
        "value": "0",
        "args": []
    }
    response = requests.post(query_url, json=post_body)
    return response.json()


# Function to repair broken files that were modified after the JSON was generated, and had their "docs" section manually written
def repair_broken_json(broken_json):
    """
    Repairs broken files that were modified after the JSON was generated, and had their "docs" section manually written.

    Parameters:
    - broken_json (str): The broken JSON string to repair.

    Returns:
    - str: Repaired JSON string.
    """

    # Function to repair the "docs" content by treating it as a single string value
    def repair_docs_as_single_string(docs_string):
        content_without_brackets = docs_string[1:-1]
        escaped_quotes_content = content_without_brackets.replace('"', '\\"')
        repaired_content = escaped_quotes_content.replace('\\\\n', '\\n')
        repaired_string = '"' + repaired_content + '"'
        return repaired_string

    # Finding all occurrences of the "docs" field within the "endpoints" objects
    docs_fields = re.findall(r'"docs":(\[.*?\])', broken_json)

    # Copying the broken content to avoid modifying it directly
    repaired_content = broken_json

    # Iterating through the "docs" fields and applying the repairs
    for docs_content in docs_fields:
        repaired_docs_content = repair_docs_as_single_string(docs_content)
        repaired_content = repaired_content.replace(docs_content, '[' + repaired_docs_content + ']')

    return repaired_content


# Function to find matching contracts for the extracted ABI JSONs and active smart contract addresses
def find_matching_contracts(abi_jsons, sc_addresses, url):
    """
    Finds matching contracts for the extracted ABI JSONs and active smart contract addresses.

    Parameters:
    - abi_jsons (List[dict]): List of ABI JSONs to match against.
    - sc_addresses (List[str]): List of smart contract addresses to match.
    - url (str): URL from where the ABI JSONs were extracted.

    Returns:
    - None
    """
    relationship_dict = {}
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    subdomain_directory = create_export_directories(domain)
    for abi_json_str in abi_jsons:
        try:
            # Escape any backslashes in the JSON string
            abi_json_str_escaped = abi_json_str.encode('unicode_escape').decode('utf-8')
            try:
                abi_json = json.loads(abi_json_str_escaped)
            except:
                abi_json = json.loads(repair_broken_json(abi_json_str))
            function_names = [endpoint["name"] for endpoint in abi_json["endpoints"]]

            # Check the first function only
            func_name = function_names[0]
            for sc_address in sc_addresses:
                response = query_function(sc_address, func_name)
                return_code = response["data"]["data"]["returnCode"]
                if return_code not in ["function not found", "contract not found"]:
                    # Check two more random functions for a match
                    random_functions = random.sample(function_names[1:], NUMBER_OF_MATCHES) if len(
                        function_names) > NUMBER_OF_MATCHES - 1 else function_names[1:]
                    match_count = 0
                    for random_func in random_functions:
                        if query_function(sc_address, random_func)["data"]["data"]["returnCode"] not in ["function not found", "contract not found"]:
                            match_count += 1
                    if match_count == len(random_functions):
                        # Inside the loop where you process ABI JSONs
                        name_field = abi_json["name"]
                        abi_json_path = export_abi_json(abi_json, name_field, subdomain_directory)
                        relationship_dict[sc_address] = abi_json_path
                        print(f"Found matching ABI JSON for {sc_address}!\nWritten ABI JSON to file at {abi_json_path}")
        except Exception as e:
            pass
    relationship_file_path = export_relationship_dict(relationship_dict, subdomain_directory)
    print(f"Written relationship JSON to file at: {relationship_file_path}")


# Function to get JS URLs from the given URL
def get_js_urls(url):
    """
    Retrieves JavaScript URLs from the given web page URL.

    Parameters:
    - url (str): URL of the web page to retrieve JS URLs from.

    Returns:
    - List[str]: List of JavaScript URLs found in the web page.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    js_urls = [urljoin(url, script['src']) for script in soup.find_all('script') if
               'src' in script.attrs and 'main' in script['src'] and script['src'].endswith('.js')]
    return js_urls


# Function to process JS URL and extract ABI JSONs
def process_js_url(js_url):
    """
    Processes a JavaScript URL to extract ABI JSONs.

    Parameters:
    - js_url (str): JavaScript URL to process.

    Returns:
    - List[str]: List of extracted ABI JSONs from the JavaScript.
    """
    # Send a request to get JS code
    response = requests.get(js_url)
    js_code = response.text

    # Find occurrences of "buildInfo" and the nearest opening brace in the JS code
    buildinfo_occurrences = find_buildinfo_and_nearest_opening_brace(js_code)

    # Extract and repair the content between the matching braces for each occurrence of "buildInfo"
    abi_jsons = []
    for occurrence in buildinfo_occurrences:
        buildinfo_content_nested = extract_matching_braces_content(js_code, occurrence[0])

        repaired_json = repair_json(buildinfo_content_nested)

        abi_jsons.append(repaired_json)
    abi_jsons = list(set(abi_jsons))
    # Extracting smart contract addresses
    extracted_addresses = extract_addresses(js_code)

    # Querying Elasticsearch to find active smart contract addresses
    active_addresses = get_active_addresses(extracted_addresses)

    # Finding matching contracts for the extracted ABI JSONs and active smart contract addresses
    find_matching_contracts(abi_jsons, active_addresses, js_url)
    return abi_jsons


# Main function to accept URL and process it
def main():
    """
    Main function to accept a URL from the user, process it, and extract ABI JSONs.
    The function prompts the user for a dApp URL, extracts JavaScript URLs, processes each JS URL,
    and extracts ABI JSONs from them.

    Returns:
    - None
    """
    url = input("Please enter the URL of the dApp to process: ")
    js_urls = get_js_urls(url)
    for js_url in js_urls:
        print(f"Processing JavaScript URL: {js_url}")
        process_js_url(js_url)


if __name__ == '__main__':
    asciiart = """
    
           ____ _____   ______      _                  _             
     /\   |  _ \_   _| |  ____|    | |                | |            
    /  \  | |_) || |   | |__  __  _| |_ _ __ __ _  ___| |_ ___  _ __ 
   / /\ \ |  _ < | |   |  __| \ \/ / __| '__/ _` |/ __| __/ _ \| '__|
  / ____ \| |_) || |_  | |____ >  <| |_| | | (_| | (__| || (_) | |   
 /_/    \_\____/_____| |______/_/\_\\__|_|  \__,_|\___|\__\___/|_|   
    
  ___        ___ _        _ _ ___ _  __ 
 | _ )_  _  / __| |___  _| | | __| |/ _|
 | _ \ || | \__ \ / / || | | | _|| |  _|
 |___/\_, | |___/_\_\\_,_|_|_|___|_|_|  
      |__/                              

    """

    print(asciiart)
    main()
