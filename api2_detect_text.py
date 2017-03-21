from base64 import b64encode  
from os import makedirs  
from os.path import join, basename , isdir, exists
from sys import argv  
import json  
import requests

from PIL import Image
from PIL import ImageDraw
from bounding_box import bounding_box

'''
Description: OCR of Image using gogle vision API
Method: 
    image_filenames = [file1,file2]
    vision = VisionApi(api_key)
    response = vision.detect_text(image_filenames)
TODO: Use Logging, Return Errors, num_retries
'''

ENDPOINT_URL = 'https://vision.googleapis.com/v1/images:annotate'  
RESULTS_DIR = 'jsons'  
if not isdir(RESULTS_DIR):
    makedirs(RESULTS_DIR)

class DEBUG_LEVEL:
    """
    Different verbose levels for vision api
    """
    NONE    = 0
    INFO    = 1
    DEBUG   = 2


# Check the level to print the polyboxes and provide the output.
# If the output level is Page, just print the text (Page does not have
# polyboxes).
def checkAndDrawBox(draw, checkType, itemName, outputText, item):
     if checkType==DEBUG_LEVEL.DEBUG:
        if itemName == "page":
            print outputText
        else:
            box = [(v.get('x', 0.0), v.get('y', 0.0))
                    for v in item['boundingBox']['vertices']]
            draw.line(box + [box[0]], width=1, fill=checkAndDrawBox.FillColor[itemName])
            # print outputText
     return
checkAndDrawBox.FillColor = {"page":'#00f0f0',"block":'#f0f000',"para":'#ff0000',"word":'#0000ff', "symbol":'#00ff00'}

def check_item_in_rect(item,rect=None):
    if rect:
        box1 = [item['boundingBox']['vertices'][0].get('x', 0.0), item['boundingBox']['vertices'][0].get('y', 0.0),
                item['boundingBox']['vertices'][2].get('x', 0.0), item['boundingBox']['vertices'][2].get('y', 0.0)]
        if bounding_box(box1= box1,box2=rect) == 1:
            return  True
        else:
            return False
    else:
        return True

def get_SymbolText(symbol,rect=None):
    output = ""
    if "property" in symbol:
        if "detectedBreak" in symbol["property"]:
            if "isPrefix" in symbol["property"]["detectedBreak"] and symbol["property"]["detectedBreak"]["isPrefix"]:
                output = get_SymbolText.breakToStringMap[symbol["property"]["detectedBreak"]["type"]] + symbol['text']
            else:
                output = symbol['text'] + get_SymbolText.breakToStringMap[symbol["property"]["detectedBreak"]["type"]] 
        else:
            output = symbol['text'] 
    else:
        output = symbol['text'] 
    return output   
get_SymbolText.breakToStringMap  = { "UNKNOWN" : "",
                                    "SPACE" : " ",
                                    "SURE_SPACE" : "\t",
                                    "EOL_SURE_SPACE" : "\r\n",
                                    "HYPHEN" : "-",
                                    "LINE_BREAK": "\n"}

def get_text_in_box(image_file, response, rect=None, verbose=DEBUG_LEVEL.NONE):
    """Run a request on a single image"""
    summary ={"pages":[], "blocks":[], "paragraphs":[], "words": [] } #Summary of text data found in box

    with open(image_file, 'rb') as image:

        # Get libraries to draw the image.
        im = Image.open(image)
        draw = ImageDraw.Draw(im)

        # Walk through the fullTextAnnotation block in the response.
        # Walk through all the Pages.
        # For each page, walk through the Blocks.
        # For each block, walk through the Paras.
        # For each para, walk through the Words.
        # For each word, consolidate the Symbols into a Word.
        # At each level, draw a box and print output based on the requested
        # output level.

        if 'fullTextAnnotation' not in response:
            print "full text not available"
            return
        fullText = response['fullTextAnnotation']
        pages = fullText['pages']
        for page in pages:
            pageText = ""
            blocks = page['blocks']
            for block in blocks:
                blockType = block['blockType']
                paras = block['paragraphs']
                blockText = ""
                if check_item_in_rect(block, rect):
                    for para in paras:
                        paraText =""
                        if check_item_in_rect(para, rect):
                            words = para['words']
                            for word in words:
                                wordText=""
                                if check_item_in_rect(word, rect):
                                    symbols = word['symbols']
                                    for symbol in symbols:
                                        symbolText = ""
                                        if check_item_in_rect(symbol, rect):
                                            symbolText = get_SymbolText(symbol, rect)
                                            checkAndDrawBox(draw, verbose, "symbol", symbolText, symbol)
                                            wordText = wordText + symbolText
                                    checkAndDrawBox(draw, verbose, "word", wordText, word)
                                    paraText = paraText + wordText
                                    summary["words"].append(wordText)
                            checkAndDrawBox(draw, verbose, "para", paraText, para)
                            blockText = blockText + paraText
                            summary["paragraphs"].append(paraText)
                    checkAndDrawBox(draw, verbose, "block", blockText, block)
                    pageText = pageText + blockText
                    summary["blocks"].append(blockText)
            checkAndDrawBox(draw, verbose, "page", pageText, page)
            summary["pages"].append(pageText)

        # Save output with the drawn polyboxes based on the requested level.
        if verbose == DEBUG_LEVEL.DEBUG:
            output_file =  "DEBUG_" +basename(image_file)
            im.save( join(RESULTS_DIR,output_file))

    return summary


def isURI(path):
    """
    Check whether given path is URI or not
    """
    #TODO: Mock function only
    return True

def make_image_data_list(image_filenames):  
    """
    image_filenames is a list of filename strings
    Returns a list of dicts formatted as the Vision API
        needs them to be
    """
    img_requests = []
    errors = {}

    for imgname in image_filenames:
        try:
            if exists(imgname):
                with open(imgname, 'rb') as f:
                    ctxt = b64encode(f.read()).decode()
                    img_requests.append({
                            'image': {'content': ctxt},
                            'features': [{
                                'type': 'TEXT_DETECTION',
                                'maxResults': 1
                            }]
                        })
            elif isURI(imgname):
                img_requests.append({
                        'image': {
                            'source': {
                              "imageUri": imgname
                              }
                            },
                        'features': [{
                            'type': 'TEXT_DETECTION',
                            'maxResults': 1
                        }]
                    })
            else:
                print("Error: {} filepath is invalid. Skipping".format(imgname))
                errors[imgname]="{} filepath is invalid. Skipping".format(imgname)
        except Exception as e:
            errors[imgname] = e

    return {"requests":img_requests, "errors":errors}

class VisionApi:
    """Construct and use the Google Vision API service."""
    def __init__(self, api_key = None, verbose = DEBUG_LEVEL.NONE):
        if api_key:
            self.api_key = api_key
            self.verbose =  verbose
        else:
            print('Error: API Key is needed for initialisation of google vision api')

    def detect_text(self, input_filenames, num_retries=3):

        if type(input_filenames) is dict:
            image_filenames = input_filenames.keys()
        else:
            image_filenames = input_filenames


        request_data = make_image_data_list(image_filenames)

        requested_files = []
        for file in image_filenames:
            if file not in request_data["errors"]:
                requested_files.append(file)

        response = requests.post(ENDPOINT_URL,
                            data=json.dumps({"requests": request_data["requests"] }).encode(),
                            params={'key': self.api_key},
                            headers={'Content-Type': 'application/json'})

        result = {}
        if response.status_code != 200 or response.json().get('error'):
            print(response.text)
        else:
            for idx, resp in enumerate(response.json()['responses']):
                #TODO: for all boxes
                imgname = requested_files[idx]
                resp["summary"] = []
                if type(input_filenames) is dict:
                    for rect in input_filenames[imgname]:
                        resp["summary"].append(get_text_in_box(image_file=imgname, response=resp, rect=rect, verbose= self.verbose))
                else:
                    resp["summary"].append(get_text_in_box(image_file=imgname, response=resp, verbose = self.verbose))
                
                result[imgname] = resp


                if self.verbose == DEBUG_LEVEL.DEBUG:
                # save to JSON file  
                    jpath = join(RESULTS_DIR, basename(imgname) + '.json')
                    with open(jpath, 'w') as f:
                        datatxt = json.dumps(resp, indent=2)
                        print(DEBUG_LEVEL.DEBUG, ": Wrote", len(datatxt), "bytes to", jpath)
                        f.write(datatxt)

                if self.verbose >= DEBUG_LEVEL.INFO :
                # print the plaintext to screen for convenience
                    print(DEBUG_LEVEL.INFO)
                    t = resp['textAnnotations'][0]
                    print("    Bounding Polygon:")
                    print(t['boundingPoly'])
                    print("    Text:")
                    print(t['description'])
        return result

    
 

if __name__ == '__main__':  
    api_key = ''
    image_filenames = ['/home/saurabh/Downloads/Aadhar_1_1.jpg']
    # image_filenames = {'/home/saurabh/Downloads/Aadhar_1_1.jpg':[[104,435,1003,641],[104,1235,1003,6041]],'http://s6.favim.com/orig/65/ask-assume-friend-life-Favim.com-575001.jpg':[]}
    # image_filenames = ['http://s6.favim.com/orig/65/ask-assume-friend-life-Favim.com-575001.jpg']
    if not api_key or not image_filenames:
        print("""
            Please supply an api key, then one or more image filenames
            """)
    else:
        vision = VisionApi(api_key,verbose=DEBUG_LEVEL.DEBUG)
        response = vision.detect_text(image_filenames)
        
        print response.keys()
