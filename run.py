# Clawdia Monet
#
# Author: Peter Jakubowski
# Date: 3/23/2025
# Description: Startup script for Clawdia Monet
#

import streamlit as st
import subprocess
import pathlib
import logging
from bs4 import BeautifulSoup
import shutil


def modify_tag_content(tag_name, new_content, favicon_filename='images/clawdia_monet.jpg'):
    index_path = pathlib.Path(st.__file__).parent / "static" / "index.html"
    logging.info(f'editing {index_path}')
    soup = BeautifulSoup(index_path.read_text(), features="html.parser")


    # if tag_name == 'link' and 'rel' in new_content.lower() and 'icon' in new_content.lower():
    #     # Modify or add favicon link tag
    #     favicon_tag = soup.find('link', {'rel': 'icon'})
    #     if favicon_tag:
    #         favicon_tag['href'] = favicon_filename
    #     else:
    #         favicon_tag = soup.new_tag('link', rel='icon', type='image/jpg', href=favicon_filename)
    #         if soup.head:
    #             soup.head.append(favicon_tag)

    target_tag = soup.find(tag_name)  # find the target tag

    if target_tag:  # if target tag exists
        target_tag.string = new_content  # modify the tag content
    else:  # if target tag doesn't exist, create a new one
        target_tag = soup.new_tag(tag_name)
        target_tag.string = new_content
        try:
            if tag_name in ['title', 'script', 'noscript'] and soup.head:
                soup.head.append(target_tag)
            elif soup.body:
                soup.body.append(target_tag)
        except AttributeError as e:
            print(f"Error when trying to append {tag_name} tag: {e}")
            return

    # Save the changes
    bck_index = index_path.with_suffix('.bck')
    if not bck_index.exists():
        shutil.copy(index_path, bck_index)  # keep a backup
    index_path.write_text(str(soup))

    return


def main():
    """

    :return:
    """

    # Example usage with modifying the title and favicon
    modify_tag_content('title', 'Clawdia Monet')
    modify_tag_content('noscript', 'Clawdia Monet paints cats')
    # modify_tag_content('link', '', favicon_filename='images/clawdia_monet.jpg')

    favicon_path = pathlib.Path(st.__file__).parent / "static" / "favicon.png"

    src_favicon = "images/favicon.png"

    subprocess.run(["cp", src_favicon, favicon_path])

    # subprocess.run(["streamlit", "run", "app.py"])

    return


if __name__ == '__main__':
    main()
