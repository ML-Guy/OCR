#!/usr/bin/env python

"""
This script uses the Vision API's OCR capabilities to find and index any text
a set of images.

"""

import argparse
# [START detect_text]
import base64
import os
import re
import sys
import json

from googleapiclient import discovery
from googleapiclient import errors
from oauth2client.client import GoogleCredentials

DISCOVERY_URL = 'https://{api}.googleapis.com/$discovery/rest?version={apiVersion}'  # noqa
BATCH_SIZE = 10


class VisionApi:
    """Construct and use the Google Vision API service."""

    def __init__(self):
        self.credentials = GoogleCredentials.get_application_default()
        self.service = discovery.build(
            'vision', 'v1', credentials=self.credentials,
            discoveryServiceUrl=DISCOVERY_URL)

    def detect_text(self, input_filenames, num_retries=3, max_results=6):
        """Uses the Vision API to detect text in the given file.
        """
        images = {}
        for filename in input_filenames:
            with open(filename, 'rb') as image_file:
                images[filename] = image_file.read()

        batch_request = []
        for filename in images:
            batch_request.append({
                'image': {
                    'content': base64.b64encode(
                            images[filename]).decode('UTF-8')
                },
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': max_results,
                }]
            })
        request = self.service.images().annotate(
            body={'requests': batch_request})

        try:
            responses = request.execute(num_retries=num_retries)
            if 'responses' not in responses:
                return {}
            text_response = {}
            for filename, response in zip(images, responses['responses']):
                if 'error' in response:
                    print("API Error for %s: %s" % (
                            filename,
                            response['error']['message']
                            if 'message' in response['error']
                            else ''))
                    continue
                if 'textAnnotations' in response:
                    text_response[filename] = response['textAnnotations']
                else:
                    text_response[filename] = []
            return text_response
        except errors.HttpError as e:
            print("Http Error for %s: %s" % (filename, e))
        except KeyError as e2:
            print("Key error: %s" % e2)
# [END detect_text]


# [START get_text]
def get_text_from_files(vision, input_filenames):
    """Call the Vision API on a file and index the results."""
    texts = vision.detect_text(input_filenames)
    with open("response.json","wb") as f:
        json.dump(texts, f)

def batch(iterable, batch_size=BATCH_SIZE):
    """Group an iterable into batches of size batch_size.

    >>> tuple(batch([1, 2, 3, 4, 5], batch_size=2))
    ((1, 2), (3, 4), (5))
    """
    b = []
    for i in iterable:
        b.append(i)
        if len(b) == batch_size:
            yield tuple(b)
            b = []
    if b:
        yield tuple(b)


def main(input_dir):

    # Create a client object for the Vision API
    vision = VisionApi()

    fileslist = ['/home/saurabh/Downloads/Aadhar_1_1.jpg']
    get_text_from_files(vision, fileslist)
    
    # Recursively construct a list of all the files in the given input
    # directory.
    # for folder, subs, files in os.walk(input_dir):
    #     for filename in files:
    #         fileslist.append(os.path.join(folder, filename))

    # for filenames in batch(fileslist):
        # get_text_from_files(vision, filenames)
# [END get_text]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Detects text in the images in the given directory.')
    parser.add_argument(
        'input_directory',
        help='the image directory you\'d like to detect text in.')
    args = parser.parse_args()

    main(args.input_directory)
