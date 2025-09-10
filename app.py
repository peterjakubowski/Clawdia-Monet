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
from storage.db import submit_log
from storage.gcs import upload_pil_image_to_gcs_and_get_url
from config import settings
import uuid
import os
from dotenv import load_dotenv
import logging
from logging_setup import setup_logging

# Configure logging
setup_logging()

# ========================
# === Streamlit Layout ===
# ========================

with Image.open("images/clawdia_monet.jpg") as icon:
    st.set_page_config(page_title="Clawdia Monet", page_icon=icon)

header = st.empty()

banner = st.empty()

buttons = st.empty()

working = st.empty()

body = st.empty()

buttons_low = st.empty()

footer_html = """<div style='text-align: center;'>
  <p><br><br>AI agent built by <a href='https://www.petes.tools' target="_blank"> Pete's Tools</a> using <a href="https://deepmind.google/technologies/gemini/" target="_blank">Google Gemini️</a> models.</p>
</div>"""

footer = st.markdown(footer_html, unsafe_allow_html=True)


# ========================
# === Helper Functions ===
# ========================

def api_config():
    """
    loads the Google genai api key and configures the service
    :return:
    """

    client = None

    # Check settings for key
    if key := settings.GOOGLE_API_KEY:
        client = genai.Client(api_key=key)
        # st.success('api key accessed from env var')
    # Check for a .env file and key
    elif load_dotenv(".env") and (key := os.getenv('GOOGLE_API_KEY')):
        client = genai.Client(api_key=key)
        # st.success('api key accessed from load_dotenv')
    # Try to load key from streamlit secrets
    else:
        try:
            client = genai.Client(api_key=st.secrets['GOOGLE_API_KEY'])
        except KeyError:
            logging.error('Configuration failed. Missing API key.')
            st.warning('Configuration failed. Missing API key.')
            st.stop()
        except FileNotFoundError:
            logging.error('Configuration failed. Missing API key.')
            st.warning('Configuration failed. Missing API key.')
            st.stop()

    if client:
        # Keep the client in session state
        st.session_state['client'] = client

    else:
        logging.warning('Client failed to configure')
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
    You have been commissioned to paint someone's adored cat or cats.
    Your patron has given you an image of their cat or cats, you must wow them with your artistic nature.
    
    You are first checking their image for the presence of cats before you paint them.
    
    # Rules
    
    * I give you an image, you tell me if there's a cat in it.
    * If there's a cat in the image, then you will be able to begin by sketching a picture from the image.
    * If there is not a cat in the image, then the photo is no use to you, since you only paint cats.
    * Send a short message to the patron about their image and what you'll do next.
    * Be creative with your message.
    * Comment about the appearance of their cat and say something you like about it.
    * If there's no cat in the image, express disappointment in receiving a photo with no cats.

    # Structured Response

    Return a structure json response with the following attributes.

    * 'is_cat': True if there is a cat False if no cat is present.

    Example 1: True
    Example 2: False

    * 'observation': Brief message to the patron about your observations of their image.

    Example 1: I couldn't find a cat in this image. I only paint cats.
    Example 2: What cute cats! This will be a beautiful painting of a cat!
    Example 3: Adorable kitten :-) I'll get started on a sketch first.
    Example 4: This is an interesting photo, but I don't see any cats! Do you have any photos of cats?
    Example 5: Your cat looks so sweet! 

    """)

    _config = types.GenerateContentConfig(system_instruction=_sys_inst.render(),
                                          temperature=1.5,
                                          top_p=0.95,
                                          response_mime_type='application/json',
                                          response_schema=CatCheck
                                          )
    try:
        _response = st.session_state.client.models.generate_content(model="gemini-2.0-flash",  # "gemini-2.0-flash-lite"
                                                                    config=_config,
                                                                    contents=["Is there a cat in this image?", _image])
    except errors.APIError as ae:
        raise ae

    return _response.parsed


def instruct_sketch(_image: Image) -> str:
    """
    Write instructions for the artist to sketch the cat in the image.

    :param _image:
    :return:
    """

    _sys_inst = Template("""You are an art instructor and excel at writing step-by-step instructions for artists to follow.

    I give you an image, you must write detailed instructions for how to transform the image into a drawing.

    # Rules

    * Focus on instructing how to make a drawing from the image.
    * Adhere to a traditional style of drawing.
    * The draw should be done with pencil on brown paper.
    * Be sure to describe the entire scene and background for the artist to draw.
    * Instruct the artist to draw all of the details in the composition.
    * Describe the cat's fur and markings so the artist can draw how the cat looks in real life.
    * Return only the finished instructions for the artist.

    """)

    _prompt = "Write detailed step-by-step instructions for how to draw this image from observation."

    _config = types.GenerateContentConfig(system_instruction=_sys_inst.render(),
                                          temperature=0.3,
                                          top_p=0.90,
                                          response_modalities=['Text'],
                                          )

    try:
        _response = st.session_state.client.models.generate_content(model="gemini-2.0-flash",
                                                                    config=_config,
                                                                    contents=[_prompt, _image])
    except errors.APIError as ae:
        raise ae

    if not _response.text:
        raise Exception("Drawing instructions error")

    return _response.text


def instruct_artist(_image: Image, _sketch: Image) -> str:
    """
    Write instructions for the artist to paint the cat in the image.

    :param _image:
    :param _sketch:
    :return:
    """

    _sys_inst = Template("""You are an artist's assistant and excel at writing instructions for the artist to follow.
    You work for Clawdia Monet, an artist that draws and paints cats.
    Clawdia has been commissioned to paint someone's adored cat or cats.
    The patron has given Clawdia an image of their cat or cats, Clawdia must wow them with their artistic nature.

    Before Clawdia begins painting, you must write detailed instructions for how to transform the image into a painting.
    
    Use the provided images of the cat as a reference.

    # Rules

    * I give you two images, the original image, and a sketch of the image.
    * Focus on explaining how to turn the drawing into a painting.
    * Choose an artistic style to adhere to.
    * Instruct Clawdia to paint the cat(s) with such detail that the patron will be able to recognize their cat(s).
    * Describe the cat's fur and markings so Clawdia can paint how the cat looks in real life.
    * Be sure to describe the entire scene and background.
    * Return the finished instructions for Clawdia Monet.

    """)

    _prompt = "Write detailed instructions for Clawdia Monet to make a painting from these images."

    _config = types.GenerateContentConfig(system_instruction=_sys_inst.render(),
                                          temperature=1.3,
                                          top_p=0.95,
                                          response_modalities=['Text'],
                                          )

    try:
        _response = st.session_state.client.models.generate_content(model="gemini-2.0-flash",
                                                                    config=_config,
                                                                    contents=[_prompt, _image, _sketch])
    except errors.APIError as ae:
        raise ae

    if not _response.text:
        raise Exception("Painting instructions error")

    return _response.text


def cat_sketch(_instructions: str, _image: Image) -> types.GenerateContentResponse:
    """
    Sketch the cat in the uploaded image.

    :param _instructions:
    :param _image:
    :return:
    """

    _prompt = Template("""You are Clawdia Monet, an artist that loves drawing cat-themed pictures.
    You have been commissioned to make a new drawing, your patron has given you a photo to draw from.
    
    Observe this photo and generate a hand drawn image from it .
    
    # Rules
    
    * Be sure to draw the entire scene and background.
    * Draw what you observe in the reference photo .
    
    # Response
    
    * Return the finished drawing.
    * Send a short message to the patron along with your finished work, no more than a sentence.
    
    Example 1: Here is the initial sketch of your beautiful cat; I look forward to bringing this composition to life with paint.
    Example 2: Here is the initial pencil sketch of your elegant white cat, set against the textured blanket, ready for the color to be added.
    
    # Instructions you must follow from your assistant
    
    {{instructions}}
    
    """)

    _config = types.GenerateContentConfig(response_modalities=['Text', 'Image'],
                                          temperature=0.6,
                                          top_p=0.95)

    _chat = st.session_state.client.chats.create(
        model=settings.GEMINI_MODEL_EXP_IMG_GEN,
        config=_config
    )

    try:
        _response = _chat.send_message(message=[_prompt.render(instructions=_instructions), _image])

    except errors.APIError as ae:
        raise ae

    return _response


def cat_paint(_instructions: str, _image: Image) -> types.GenerateContentResponse:
    """
    Paint the cat in the sketched image.

    :param _instructions:
    :param _image:
    :return:
    """

    _prompt = Template("""You are Clawdia Monet, an artist that draws and paints cats.
    You have been commissioned to paint someone's adored cat(s).
    Your patron has given you an image of their cat(s), you must wow them with your artistic nature.
    
    You just finished sketching out the cat(s) for your painting, so its time to paint!
    Use this sketch of a cat(s) as a reference and turn it into a painting.
    
    # Rules
    
    * Paint a picture of the cat(s)!
    * Be sure to paint the entire scene and background.
    * Return the finished painting.
    
    # Response
    
    * Send a short message to the patron along with your finished work, no more than a sentence.
    
    Example 1: Here is the finished painting of your beautiful cat, I hope you adore it!
    Example 2: I finished the painting of your cats enjoying a winter skate with many friends on a crisp, snowy day!
    
    # Instructions you must follow from your assistant
    
    {{instructions}}
    
    """)

    _config = types.GenerateContentConfig(response_modalities=['Text', 'Image'],
                                          temperature=0.6,
                                          top_p=0.95)

    _chat = st.session_state.client.chats.create(
        model=settings.GEMINI_MODEL_EXP_IMG_GEN,  # gemini-2.0-flash-preview-image-generation",
        config=_config
    )

    try:
        _response = _chat.send_message(message=[_prompt.render(instructions=_instructions), _image])

    except errors.APIError as ae:
        raise ae

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
            logging.warning(f"Error: Image file not found {st.session_state.file.name}")
            st.warning(f"Error: Image file not found {st.session_state.file.name}")
        except Image.UnidentifiedImageError:
            logging.warning(f"Error: Cannot identify image file {st.session_state.file.name}")
            st.warning(f"Error: Cannot identify image file {st.session_state.file.name}")
        except IOError:
            logging.warning(f"Error: An I/O error occurred when opening {st.session_state.file.name}")
            st.warning(f"Error: An I/O error occurred when opening {st.session_state.file.name}")
        except ValueError:
            logging.warning("Error: Invalid mode or file path.")
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

    banner.write("May I paint your cat? Upload a photo with a cat in it to get started 😺")

    if (file := body.file_uploader(label="Upload Cat Photo",
                                   accept_multiple_files=False,
                                   type=["jpg", "jpeg", "png"],
                                   key='upload',
                                   # on_change=open_image_workflow(),
                                   label_visibility='hidden')):
        st.session_state.file = file
        logging.info("Opening the uploaded image...")
        open_image_workflow()

        return st.rerun()


def cat_check_workflow():
    """
    Workflow for checking whether the image is of a cat or not.

    :return:
    """

    with banner, st.spinner("Looking over image..."):
        logging.info("Looking over image to check if there is a cat.")
        # show the image
        body.image(st.session_state.image)
        # check if this is a cat
        try:
            response = cat_check(_image=st.session_state.image)
        except errors.APIError as ae:
            logging.warning(ae.message)
            banner.warning(ae.message)
            buttons.button('Try Again')
            st.stop()
        else:
            st.session_state.is_cat = response

    if st.session_state.is_cat.is_cat:
        return st.rerun()

    logging.info(st.session_state.is_cat.observation)
    banner.warning(st.session_state.is_cat.observation)
    buttons.button("Start Over", on_click=clear_session)

    return st.stop()


def draw_cat_workflow():
    """
    Workflow for drawing the sketch of the cat.

    :return:
    """

    with banner.container():
        st.write(st.session_state.is_cat.observation)

    with working.container(), st.spinner("Sketching...", show_time=True):
        body.image(st.session_state.image)
        # instruct the artist how to draw from the image then sketch an image of the cat
        try:
            logging.info("Preparing to sketch, generating instructions for the artist...")
            instructions = instruct_sketch(_image=st.session_state.image)
            logging.info("Generating a sketch from image and instructions...")
            response = cat_sketch(_image=st.session_state.image, _instructions=instructions)
        except errors.APIError as ae:
            logging.error(ae.message)
            st.warning(ae.message)
            buttons.button("Try Again")
            st.stop()

    working.empty()
    banner.empty()

    # check the response for text and images
    with banner.container():
        for _part in response.candidates[0].content.parts:
            if _part.text is not None:
                st.write(_part.text)
            if _part.inline_data is not None:
                logging.info("New drawing generated and ready to display.")
                st.session_state.drawing = Image.open(BytesIO(_part.inline_data.data))
                # load the cat sketch
                body.image(st.session_state.drawing)
                try:
                    # upload image to google cloud storage and get public url
                    artwork_image_url = upload_pil_image_to_gcs_and_get_url(
                        image_pil=st.session_state.drawing,
                        bucket_name=settings.GCS_BUCKET_NAME,
                        destination_blob_name=f"{str(uuid.uuid4())}.png",
                        project_id=settings.GCP_PROJECT_ID,
                        image_format='PNG',
                        content_type='image/png'
                    )
                    st.session_state.artwork_image_url = artwork_image_url

                except Exception:
                    logging.error("An error occurred while attempting to upload image to cloud storage.")
                    pass

                submit_log(workflow_status="sketch")

    if 'drawing' not in st.session_state:
        logging.warning("Something went wrong. Try again.")
        banner.warning("Something went wrong. Try again.")

    # create two columns in the buttons container
    col1, col2 = buttons.columns(2, gap="small")
    # create two columns for buttons inside the left column
    but1, but2 = col1.columns(2, gap="small")
    # place buttons in the columns
    with but1:
        st.button(label="Sketch Again", on_click=clear_drawing, use_container_width=True)

    with but2:
        st.button("Start Painting", use_container_width=True, type="primary")

    buttons_low.button("Start Over", on_click=clear_session)

    return st.stop()


def paint_cat_workflow():
    """
    Workflow for painting from a sketch.

    :return:
    """

    # show the drawing
    body.image(st.session_state.drawing)

    with working.container(), st.spinner("Preparing to paint...", show_time=True):
        # get instructions for the painting
        logging.info("Preparing to paint, generating instructions for the artist...")
        try:
            instructions = instruct_artist(_image=st.session_state.image, _sketch=st.session_state.drawing)
        except errors.APIError as ae:
            logging.error(ae.message)
            banner.warning(ae.message)
            buttons.button("Try Again")
            st.stop()
        except Exception as ex:
            logging.error(ex)
            banner.warning(ex)
            buttons.button("Try Again")
            st.stop()

    with working.container(), st.spinner("Painting...", show_time=True):
        # generate the painting
        logging.info("Generating a painting from sketch and instructions...")
        try:
            response = cat_paint(_instructions=instructions, _image=st.session_state.drawing)
        except errors.APIError as ae:
            logging.error(ae.message)
            banner.warning(ae.message)
            buttons.button("Try Again")
            st.stop()

    working.empty()

    # check the response for text and images
    with banner.container():
        for _part in response.candidates[0].content.parts:
            if _part.text is not None:
                st.write(_part.text.strip())
            if _part.inline_data is not None:
                logging.info("New painting generated and ready to display.")
                # load the cat painting
                st.session_state.painting = Image.open(BytesIO(_part.inline_data.data))
                # display the cat painting
                body.image(st.session_state.painting)
                try:
                    # upload masked image to google cloud storage and get public url
                    artwork_image_url = upload_pil_image_to_gcs_and_get_url(
                        image_pil=st.session_state.painting,
                        bucket_name=settings.GCS_BUCKET_NAME,
                        destination_blob_name=f"{str(uuid.uuid4())}.png",
                        project_id=settings.GCP_PROJECT_ID,
                        image_format='PNG',
                        content_type='image/png'
                    )
                    st.session_state.artwork_image_url = artwork_image_url
                except Exception:
                    logging.error("An error occurred while attempting to upload the painting to cloud storage.")
                    pass

                submit_log(workflow_status="painting")

        if 'painting' not in st.session_state:
            logging.warning("Something went wrong and the painting could not be generated.")
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

    # Check the user's locale to make sure it's in the US
    if st.session_state.get('locale', 'missing') == 'missing':
        try:
            locale = st.context.locale.split('-')[-1].lower()
        except Exception as e:
            logging.error("Something went wrong 😿")
            banner.warning("Something went wrong 😿")
            st.stop()
        else:
            st.session_state['locale'] = locale

        if locale != 'us':
            logging.info("Sorry, some of this app's features are not supported in your language 😿.")
            banner.warning("Sorry, some of this app's features are not supported in your language 😿.")
            st.stop()

    # Start by uploading a file
    if 'image' not in st.session_state:
        # Run upload workflow
        upload_workflow()
    # Check if the image is of a cat
    elif 'image' in st.session_state and 'is_cat' not in st.session_state:
        # Run cat check
        logging.info("Running cat check...")
        cat_check_workflow()
    elif 'drawing' not in st.session_state and 'is_cat' in st.session_state and st.session_state.is_cat.is_cat:
        # Run drawing agent
        logging.info("Running drawing workflow...")
        draw_cat_workflow()
    elif 'drawing' in st.session_state:
        # Start painting!
        logging.info("Running painting workflow...")
        paint_cat_workflow()
    else:
        logging.info("Whoa! How did you end up here?")
        banner.write("Whoa! How did you end up here?")
        buttons.button("Start Over", on_click=clear_session)

    return st.stop()


# RUN THE APP
app()
