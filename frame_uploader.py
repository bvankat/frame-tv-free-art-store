from samsungtvws import SamsungTVWS


def upload_and_show(tv_ip: str, image_bytes: bytes, matte: str = "none") -> str:
    """
    Uploads the image to the Frame's Art Mode gallery and sets it as
    the currently displayed piece. Returns the content_id, which
    can be cached to avoid re-uploading the same artwork later.

    NOTE: on the very first connection ever made to this TV, it will
    show an "Allow access?" popup on screen - you must accept it
    (once) with the remote before this will work.
    """
    tv = SamsungTVWS(host=tv_ip)
    art = tv.art()

    content_id = art.upload(image_bytes, file_type="JPEG", matte=matte)
    art.select_image(content_id, show=True)

    tv.close()
    return content_id


def ensure_art_mode(tv_ip: str):
    tv = SamsungTVWS(host=tv_ip)
    art = tv.art()
    if not art.get_artmode():
        art.set_artmode("on")
    tv.close()
