# Clawdia Monet
#
# Author: Peter Jakubowski
# Date: 3/23/2025
# Description: Clawdia Monet paints cats
#

import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO
from image_utils.image_utils import rescale_width_height
from jinja2 import Template
from google import genai
from google.genai import types
from google.genai import errors
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import time

# =====================
# === Constant Vars ===
# =====================

SAFETY_SETTINGS = [types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                       threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
                   types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                       threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
                   types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                       threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
                   types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                       threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH)]

# ========================
# === Streamlit Layout ===
# ========================

header = st.empty()

banner = st.container()

buttons = st.empty()

body = st.empty()


# ========================
# === Helper Functions ===
# ========================

def api_config():
    """
    loads the Google genai api key and configures the service
    :return:
    """

    client = None

    # Check env vars for key
    if key := os.getenv('GOOGLE_API_KEY'):
        client = genai.Client(api_key=key)
    # Check for a .env file and key
    elif load_dotenv() and (key := os.getenv('GOOGLE_API_KEY')):
        client = genai.Client(api_key=key)
    # Try to load key from streamlit secrets
    else:
        try:
            client = genai.Client(api_key=st.secrets['GOOGLE_API_KEY'])
        except KeyError:
            st.warning('Configuration failed. Missing API key.')
            st.stop()
        except FileNotFoundError:
            st.warning('Configuration failed. Missing API key.')
            st.stop()
    if client:
        # Keep the client and model names in
        # st.session_state['models'] = genai_model_names
        st.session_state['client'] = client

    else:
        st.warning('Client failed to configure')
        st.stop()


def process_message(_part: types.Part) -> None:
    """
    Add content parts to the chat and display them.

    :param _part: Message to add to the chat
    :return: None
    """

    assert 'messages' in st.session_state, "Cannot find messages in the session state."

    _content = []

    if _part.text is not None:
        _content.append(_part.text)
    if _part.executable_code is not None:
        _content.append(_part.executable_code.code)
    if _part.code_execution_result is not None:
        _content.append(_part.code_execution_result.output)
    if _part.inline_data is not None:
        img = Image.open(BytesIO(_part.inline_data.data))
        _content.append(img)

    for c in _content:
        # add the message to the chat
        st.session_state.messages.append({"role": "assistant", "content": c})
        # display the message in the chat
        st.chat_message("assistant").write(c)

    return


def clear_drawing():
    """
    Clear the drawing from the session state

    :return:
    """

    st.session_state.pop('drawing', None)


def clear_painting():
    """
    Clear the painting from the session state

    :return:
    """

    st.session_state.pop('painting', None)


def clear_session():
    """
    Clear the session and start over.

    :return:
    """

    st.session_state.pop('upload', None)
    st.session_state.pop('image', None)
    st.session_state.pop('is_cat', None)
    st.session_state.pop('drawing', None)


# ===================
# === Data Models ===
# ===================

class CatCheck(BaseModel):
    is_cat: bool  # True or False
    observation: str  # Your observations of the image


# ====================
# === GenAI Agents ===
# ====================

def cat_check(_image: Image) -> BaseModel:
    """
    Check if there's a cat in the uploaded image.

    :param _image:
    :return:
    """

    _sys_inst = Template("""You are Clawdia Monet, an artist that draws and paints cats.
    You have been commissioned to paint someone's adored cat.
    Your patron has given you an image of their cat, you must wow them with your artistic nature.
    
    You are first checking their image for the presence of cats before you paint them.
    
    # Rules
    
    * I give you an image, you tell me if there's a cat in it.
    * If there's a cat in the image, then you will be able to paint a picture from the image.
    * If there is not a cat in the image, then the photo is no use to you, since you only paint cats.
    * Send a short message to the patron about their image and what you'll do next.

    # Structured Response

    Return a structure json response with the following attributes.

    * 'is_cat': True if there is a cat False if no cat is present.

    Example 1: True
    Example 2: False

    * 'observation': Brief message to the patron about your observations of their image.

    Example 1: I couldn't find a cat in this image. I only paint cats.
    Example 2: What a cute cat! This will be a beautiful painting of a cat!
    Example 3: Adorable kitten :-) I'll get started on a sketch.

    """)

    _config = types.GenerateContentConfig(system_instruction=_sys_inst.render(),
                                          temperature=1.0,
                                          top_p=0.95,
                                          response_mime_type='application/json',
                                          response_schema=CatCheck
                                          )

    _response = st.session_state.client.models.generate_content(model="gemini-2.0-flash-exp",
                                                                config=_config,
                                                                contents=["Is there a cat in this image?", _image])

    return _response.parsed


def instruct_artist(_image: Image, _sketch: Image) -> str:
    """
    Write instructions for the artist to paint the cat in the image.

    :param _image:
    :param _sketch:
    :return:
    """

    _sys_inst = Template("""You are an artist's assistant and excel at writing instructions for the artist to follow.
    You work for Clawdia Monet, an artist that draws and paints cats.
    Clawdia has been commissioned to paint someone's adored cat.
    The patron has given Clawdia an image of their cat, Clawdia must wow them with their artistic nature.

    Before Clawdia begins painting, you must write instructions for how to transform the image into a painting.
    
    Use the provided images of the cat as a reference.

    # Rules

    * I give you two images, the original image, and a sketch of the image.
    * Focus on explaining how to turn the drawing into an oil painting.
    * Instruct Clawdia to paint the cat with such detail that the patron will be able to recognize that it is their cat.
    * Be sure to describe the entire scene and background.
    * Return the finished instructions.

    """)

    _prompt = "Write detailed instructions for Clawdia Monet to make an oil painting from these images."

    _config = types.GenerateContentConfig(system_instruction=_sys_inst.render(),
                                          temperature=1.0,
                                          top_p=0.95,
                                          response_modalities=['Text'],
                                          )

    _response = st.session_state.client.models.generate_content(model="gemini-2.0-flash-001",
                                                                config=_config,
                                                                contents=[_prompt, _image, _sketch])

    return _response


def cat_sketch(_image: Image) -> Image:
    """
    Sketch the cat in the uploaded image.

    :param _image:
    :return:
    """

    _prompt = Template("""You are Clawdia Monet, an artist that draws and paints cats.
    You have been commissioned to paint someone's adored cat.
    Your patron has given you an image of their cat, you must wow them with your artistic nature.
    
    Before you begin painting, you must sketch out the image.
    Use this image of a cat as a reference and sketch a hand drawn image.
    
    # Rules
    
    * Draw the cat with black and white charcoal on brown paper.
    * Be sure to draw the entire scene and background.
    * Return the finished drawing.
    * Send a short message to the patron along with your finished work, no more than a sentence.
    
    """)

    _config = types.GenerateContentConfig(response_modalities=['Text', 'Image'],
                                          temperature=0.6,
                                          top_p=0.95)

    _chat = st.session_state.client.chats.create(model="gemini-2.0-flash-exp",
                                                 config=_config)

    _response = _chat.send_message(message=[_prompt.render(), _image])

    return _response


def cat_paint(_instructions: str, _image: Image) -> Image:
    """
    Paint the cat in the sketched image.

    :param _instructions:
    :param _image:
    :return:
    """

    _prompt = Template("""You are Clawdia Monet, an artist that draws and paints cats.
    You have been commissioned to paint someone's adored cat.
    Your patron has given you an image of their cat, you must wow them with your artistic nature.
    
    You just finished sketching out the cat for your painting, so its time to paint!
    Use this sketch of a cat as a reference and turn it into a painting.
    
    # Rules
    
    * Paint the cat with oil paint.
    * Be sure to paint the entire scene and background.
    * Return the finished painting.
    * Send a short message to the patron along with your finished work, no more than a sentence.
    
    # Instructions to follow
    
    {{instructions}}
    
    """)

    _config = types.GenerateContentConfig(response_modalities=['Text', 'Image'],
                                          temperature=0.6,
                                          top_p=0.95)

    _chat = st.session_state.client.chats.create(model="gemini-2.0-flash-exp",
                                                 config=_config)

    _response = _chat.send_message(message=[_prompt.render(instructions=_instructions), _image])

    return _response


# =====================
# === Configure API ===
# =====================

if 'client' not in st.session_state:
    api_config()


# =====================
# === Streamlit App ===
# =====================

def open_image_workflow():
    """

    :return:
    """

    if 'file' in st.session_state and st.session_state.file.type in ('image/jpeg', 'image/png'):
        # try to open the uploaded file as an image with Pillow
        try:
            image = ImageOps.exif_transpose(Image.open(st.session_state.file))
        except FileNotFoundError:
            st.warning(f"Error: Image file not found {st.session_state.file.name}")
        except Image.UnidentifiedImageError:
            st.warning(f"Error: Cannot identify image file {st.session_state.file.name}")
        except IOError:
            st.warning(f"Error: An I/O error occurred when opening {st.session_state.file.name}")
        except ValueError:
            st.warning("Error: Invalid mode or file path.")
        # add the open image to the chat, display it, and append it to our list of prompt content
        else:
            # Resize the image if its max length exceeds allowed size
            if max(image.size) > 1024:
                # Retrieve the image's original dimensions
                w, h = image.size
                # Rescale the image's dimensions where size is the longest edge
                rw, rh = rescale_width_height(width=w, height=h, size=1024)
                # Resize the image with new dimensions
                image = image.resize((rw, rh), Image.Resampling.BICUBIC)
            st.session_state['image'] = image

    return


def upload_workflow():
    """
    Workflow for uploading an image to the service.

    :return:
    """

    banner.write("May I paint your cat? Upload an image to get started 😺")

    if (file := body.file_uploader(label="Upload Cat Photo",
                                   accept_multiple_files=False,
                                   type=['jpg', 'png'],
                                   key='upload',
                                   # on_change=open_image_workflow(),
                                   label_visibility='hidden')):
        st.session_state.file = file
        open_image_workflow()

        return st.rerun()


def cat_check_workflow():
    """
    Workflow for checking whether the image is of a cat or not.

    :return:
    """

    with banner, st.spinner("Looking over image..."):
        # show the image
        body.image(st.session_state.image)
        # check if this is a cat
        try:
            response = cat_check(_image=st.session_state.image)
        except errors.APIError as ae:
            banner.warning(ae.message)
            st.stop()
        else:
            st.session_state.is_cat = response

    if st.session_state.is_cat.is_cat:
        banner.write(st.session_state.is_cat.observation)
        time.sleep(3)
        return st.rerun()

    banner.warning(st.session_state.is_cat.observation)

    return st.stop()


def draw_cat_workflow():
    """
    Workflow for drawing the sketch of the cat.

    :return:
    """

    with banner, st.spinner("Sketching...", show_time=True):
        body.image(st.session_state.image)
        # check if this is a cat
        try:
            response = cat_sketch(_image=st.session_state.image)
        except errors.APIError as ae:
            banner.warning(ae.message)
            st.stop()
        else:
            # check the response for text and images
            for _part in response.candidates[0].content.parts:
                if _part.text is not None:
                    banner.write(_part.text)
                if _part.inline_data is not None:
                    st.session_state.drawing = Image.open(BytesIO(_part.inline_data.data))
                    # clear body container
                    # body.empty()
                    # load the cat sketch
                    body.image(st.session_state.drawing)

    if 'drawing' not in st.session_state:
        st.warning("Something went wrong. Try again.")

    # create two columns in the buttons container
    col1, col2 = buttons.columns(2, gap="small")
    # create two columns for buttons inside the left column
    but1, but2 = col1.columns(2, gap="small")
    # place buttons in the columns
    with but1:
        st.button(label="Sketch Again", on_click=clear_drawing, use_container_width=True)

    with but2:
        st.button("Start Painting", use_container_width=True, type="primary")

    return st.stop()


def paint_cat_workflow():
    """
    Workflow for painting from a sketch.

    :return:
    """

    body.image(st.session_state.drawing)

    with banner, st.spinner("Preparing to paint...", show_time=True):
        # get instructions for the painting
        try:
            response = instruct_artist(_image=st.session_state.image, _sketch=st.session_state.drawing)
        except errors.APIError as ae:
            banner.warning(ae.message)
            buttons.button("Try Again")
            st.stop()
        else:
            # check the response for text and images
            instructions = response

    with banner, st.spinner("Painting...", show_time=True):
        # generate the painting
        try:
            response = cat_paint(_instructions=instructions, _image=st.session_state.drawing)
        except errors.APIError as ae:
            banner.warning(ae.message)
            st.stop()
        else:
            # check the response for text and images
            for _part in response.candidates[0].content.parts:
                if _part.text is not None:
                    banner.write(_part.text)
                if _part.inline_data is not None:
                    st.session_state.painting = Image.open(BytesIO(_part.inline_data.data))
                    # clear body container
                    # body.empty()
                    # load the cat sketch
                    body.image(st.session_state.painting)

    if 'painting' not in st.session_state:
        st.warning("Something went wrong. Try again.")

    # create two columns in the buttons container
    col1, col2 = buttons.columns(2, gap="small")
    # create two columns for buttons inside the left column
    but1, but2 = col1.columns(2, gap="small")
    # place buttons in the columns
    with but1:
        st.button(label="Paint Again", on_click=clear_painting, use_container_width=True)

    with but2:
        st.button("Start Over", on_click=clear_session, use_container_width=True, type="primary")

    return st.stop()


def app():
    """
    The main app loop

    :return:
    """

    # Display the page title
    header.title("🎨🐈 Clawdia Monet")

    # Start by uploading a file
    if 'image' not in st.session_state:

        # Run upload workflow
        upload_workflow()

    # Check if the image is of a cat
    elif 'image' in st.session_state and 'is_cat' not in st.session_state:

        # Run cat check
        cat_check_workflow()

    elif 'drawing' not in st.session_state and 'is_cat' in st.session_state and st.session_state.is_cat.is_cat:

        # Run drawing agent
        draw_cat_workflow()

    elif 'drawing' in st.session_state:

        # Start painting!
        paint_cat_workflow()

    else:

        banner.write("Here we are!")

        buttons.button("Start Over", on_click=clear_session)

    return st.stop()


# RUN THE APP
app()
