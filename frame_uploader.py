from samsungtvws import SamsungTVWS

# The library defaults to a blocking socket (timeout=None), which would let a
# run hang indefinitely against a TV that's off or off-network - and under
# launchd that means a stuck process every hour. The probe runs first and
# bails out fast; the transfer paths get a lot more room, since the timeout
# applies per socket read and an upload moves several MB.
PROBE_TIMEOUT = 10
TRANSFER_TIMEOUT = 120


def get_art_mode(tv_ip: str, timeout: float = PROBE_TIMEOUT) -> str | None:
    """
    Returns "on" if the Frame is currently showing art, "off" if the TV is
    being used for something else, or None if it couldn't be reached.

    This is how we avoid hijacking the screen: the TV reports PowerState
    "on" both while you're watching something and while it's in Art Mode,
    so art mode status is the only signal that tells the two apart.
    """
    try:
        tv = SamsungTVWS(host=tv_ip, timeout=timeout)
        try:
            return tv.art().get_artmode()
        finally:
            tv.close()
    except Exception as e:
        # Off, asleep, or off-network. Not worth a traceback in the log -
        # the caller treats "can't tell" the same as "don't touch it".
        print(f"Could not read art mode from the TV ({type(e).__name__}: {e}).")
        return None


def upload_and_show(tv_ip: str, image_bytes: bytes, matte: str = "none") -> str:
    """
    Uploads the image to the Frame's Art Mode gallery and sets it as
    the currently displayed piece. Returns the content_id, which
    can be cached to avoid re-uploading the same artwork later.

    Only call this when the TV is already in Art Mode (see get_art_mode) -
    selecting an image with show=True is what pulls the screen over to art.

    NOTE: on the very first connection ever made to this TV, it will
    show an "Allow access?" popup on screen - you must accept it
    (once) with the remote before this will work.
    """
    tv = SamsungTVWS(host=tv_ip, timeout=TRANSFER_TIMEOUT)
    art = tv.art()

    content_id = art.upload(image_bytes, file_type="JPEG", matte=matte)
    art.select_image(content_id, show=True)

    tv.close()
    return content_id


def select_existing(tv_ip: str, content_id: str):
    """
    Shows a piece that's already in the TV's gallery from an earlier run,
    so we don't re-download and re-upload artwork the Frame already has.
    """
    tv = SamsungTVWS(host=tv_ip, timeout=TRANSFER_TIMEOUT)
    tv.art().select_image(content_id, show=True)
    tv.close()
