from reportlab.pdfgen.canvas import Canvas
from PIL import Image
import io

buf = io.BytesIO()
canvas = Canvas(filename=buf)
with Image.open("img.jpg").convert("RGBA") as page:
    page_width, page_height = page.size
    draw_width, draw_height = page_width, page_height
    if page_width > page_height:
        canvas.setPageSize((draw_width, draw_height))
    else:
        canvas.setPageSize((draw_width, draw_height))
    canvas.drawInlineImage(page, 0, 0, width=draw_width, height=draw_height)
canvas.save()
print(buf.getvalue())
with open("file.pdf", "w") as file:
    file.write(str(buf.getvalue()))