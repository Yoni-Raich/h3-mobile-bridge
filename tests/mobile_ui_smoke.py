"""Browser proof of mobile layout and multipart settings, without GPU jobs.

Run against a built bridge: H3_TEST_URL defaults to http://127.0.0.1:8787.
All generation POSTs are intercepted; no test output is saved in the database.
"""
import base64
import io
import json
import os
import wave
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    base = os.environ.get("H3_TEST_URL", "http://127.0.0.1:8787")
    output = Path(os.environ.get("H3_SCREENSHOT_DIR", str(Path(__file__).parent / "state" / "ui-proof")))
    output.mkdir(parents=True, exist_ok=True)
    errors, submissions, widths = [], [], []

    def capture(route):
        request = route.request
        if request.method != "POST":
            route.continue_()
            return
        message = BytesParser(policy=default).parsebytes(
            ("Content-Type: " + request.headers["content-type"] + "\r\n\r\n").encode()
            + (request.post_data_buffer or b"")
        )
        fields, files = {}, {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if part.get_filename():
                files[name] = part.get_payload(decode=True)
            else:
                fields[name] = part.get_content().strip()
        assert request.headers.get("x-csrf-token"), "Missing CSRF token"
        submissions.append((fields, files))
        route.fulfill(status=200, content_type="application/json", body='{"jobs": []}')

    def assert_fits(page):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow"
        nav = page.locator('.page-tabs').bounding_box()
        assert nav and nav['y'] + nav['height'] <= page.viewport_size['height'] + 1

    def send(page):
        page.get_by_role("button", name="צור וידאו", exact=True).click()
        # Long/high-resolution jobs keep the existing workload review.
        dialog = page.get_by_role("dialog")
        if dialog.is_visible():
            dialog.get_by_role("button", name="הוסף בכל זאת").click()
        expect(page.get_by_role("tab", name="תור", exact=False)).to_have_attribute("aria-selected", "true")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.route("**/api/jobs", capture)
        page.goto(base, wait_until="domcontentloaded")
        expect(page.get_by_role("radio", name="דיבוב", exact=False)).to_be_enabled(timeout=15000)
        assert page.locator("html").get_attribute("dir") == "rtl"
        expect(page.locator(".page-tabs button")).to_have_count(4)

        for width in (320, 390, 720, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            assert_fits(page)
            widths.append(width)
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_text("מנוע פעיל", exact=True)).to_be_visible(timeout=20000)
        page.screenshot(path=str(output / "mobile-create.png"))

        page.locator(".preset-chips button").nth(1).click()
        expect(page.locator(".preset-chips button").nth(1)).to_have_attribute("aria-pressed", "true")
        expect(page.locator('.profile-summary')).to_contain_text('1056x608')
        page.get_by_role("textbox", name="תיאור הסרטון").fill("A calm cinematic forest with rain")
        send(page)
        fields, _ = submissions[-1]
        assert fields["engine"] == "turbo" and fields["encoder"] == "native"
        assert fields["steps"] == "4" and fields["megapixels"] == "0.6"
        assert fields["turbo_profile"] == "official", fields

        page.get_by_role("tab", name="יצירה", exact=True).click()
        page.get_by_role("radio", name="דיבוב", exact=False).click()
        page.locator(".generation-heading").click()
        expect(page.locator(".lip-engine-toggle button").first).to_have_attribute("aria-pressed", "true")
        expect(page.locator(".steps-range")).to_have_value("4")
        # Six seconds of WAV exercises metadata and trimming to the five-second shot.
        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 16000 * 6)
        page.locator('.audio-dropzone input').set_input_files({"name": "smoke.wav", "mimeType": "audio/wav", "buffer": audio.getvalue()})
        page.locator('.lip-sync-inputs .dropzone input').first.set_input_files({
            "name": "smoke.png", "mimeType": "image/png",
            "buffer": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5N8AAAAASUVORK5CYII="),
        })
        expect(page.locator('.audio-trim-range')).to_be_visible()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(output / "mobile-lipsync.png"))
        send(page)
        fields, files = submissions[-1]
        assert fields["mode"] == "lip_sync" and fields["engine"] == "turbo"
        assert fields["turbo_profile"] == "v1" and fields["steps"] == "4"
        assert fields["experimental_turbo_lip_sync"] == "true" and fields["encoder"] == "native"
        assert "first_frame" in files and "audio" in files
        assert fields["audio_start"] == "0" and fields["duration"] == "5"
        # The server trims the original upload using audio_start and duration.
        with wave.open(io.BytesIO(files["audio"]), "rb") as wav:
            assert abs(wav.getnframes() / wav.getframerate() - 6) < .1

        page.get_by_role("tab", name="ספרייה", exact=False).click()
        assert_fits(page)
        page.screenshot(path=str(output / "mobile-library.png"))
        for title, selector, filename in (("מערכת", ".hw-panel", "mobile-system.png"),
                                          ("תמונות", ".image-gen-studio", "mobile-images.png"),
                                          ("הפקה", ".ps-root", "mobile-production.png")):
            page.locator(".page-tabs").get_by_role("button", name=title, exact=True).click()
            expect(page.locator(selector)).to_be_visible()
            page.wait_for_timeout(700)
            assert_fits(page)
            page.screenshot(path=str(output / filename))

        # A saved manual profile survives a reload and the recommended preset.
        page.locator(".page-tabs").get_by_role("button", name="סטודיו", exact=True).click()
        page.get_by_role("tab", name="יצירה", exact=True).click()
        page.get_by_role("radio", name="טקסט בלבד", exact=False).click()
        if not page.locator('.generation-panel').evaluate('el => el.open'):
            page.locator('.generation-heading').click()
        page.locator('.turbo-profile-toggle button').nth(1).click()
        page.reload(wait_until="domcontentloaded")
        page.locator('.generation-heading').click()
        expect(page.locator('.turbo-profile-toggle button').nth(1)).to_have_attribute('aria-pressed', 'true')
        assert not errors, errors
        result = {"widths": widths, "intercepted_jobs": [item[0] for item in submissions], "page_errors": errors,
                  "gpu_jobs_submitted": 0, "screenshots": str(output)}
        (output / "mobile-ui-proof.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
