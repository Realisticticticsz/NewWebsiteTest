import os
import random
import string
import threading
import time
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    send_from_directory,
    session,
    make_response,
)

app = Flask(__name__)
app.secret_key = "my_super_secret_key"

temp_links = {}

def cleanup_links():
    while True:
        now = datetime.now()
        keys_to_remove = []
        for key, value in temp_links.items():
            if now - value["created_at"] > timedelta(hours=4):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            print(f"Удаление просроченной ссылки: {key}")
            del temp_links[key]
        time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_links)
cleanup_thread.daemon = True
cleanup_thread.start()


@app.route("/")
def index():
    images = [f"sc{str(i).zfill(2)}.jpg" for i in range(11)]
    return render_template("index.html", images=images)


@app.route("/create_link", methods=["POST"])
def create_link():
    selected_image = request.form.get("selected_image")
    if selected_image:
        session["selected_image"] = selected_image
        return redirect(url_for("choose_path"))
    return redirect(url_for("index"))


@app.route("/choose_path")
def choose_path():
    if "selected_image" not in session:
        return redirect(url_for("index"))
    return render_template("choose.html")


@app.route("/generate_link/<path_type>")
def generate_link(path_type):
    if "selected_image" not in session:
        return redirect(url_for("index"))
    
    return render_template("generate.html", path_type=path_type)


@app.route("/process_generation", methods=["POST"])
def process_generation():
    path_type = request.form.get("path_type")
    custom_text = request.form.get("custom_text")

    if not path_type or "selected_image" not in session:
        return redirect(url_for("index"))

    if not custom_text:
        chars = string.ascii_letters + string.digits
        generated_text = "".join(random.choice(chars) for _ in range(10))
    else:
        generated_text = custom_text

    if path_type == "download":
        unique_path = f"{path_type}/{generated_text}.zip"
    else:
        unique_path = f"{path_type}/{generated_text}"

    selected_image = session.get("selected_image")

    temp_links[unique_path] = {
        "image": selected_image,
        "created_at": datetime.now(),
    }

    generated_url = url_for("serve_link", unique_path=unique_path, _external=True)
    return render_template("link.html", url=generated_url)


# Новый маршрут для принятия куки
@app.route("/cookie_consent")
def cookie_consent():
    return render_template('cookie_consent_page.html', redirect_url=request.args.get('redirect_url'))


# Обработка сгенерированной ссылки
@app.route("/<path:unique_path>")
def serve_link(unique_path):
    if unique_path in temp_links:
        # Проверяем, принял ли пользователь куки
        if request.cookies.get('cookies_accepted') == 'true':
            image_name = temp_links[unique_path]["image"]
            return render_template("view_image.html", image_name=image_name)
        else:
            # Если куки не приняты, перенаправляем на страницу согласия
            redirect_url = request.url
            return redirect(url_for('cookie_consent', redirect_url=redirect_url))
    return "Ссылка не найдена или просрочена", 404


# Маршрут для сохранения куки
@app.route("/accept_cookies/<status>")
def accept_cookies(status):
    redirect_url = request.args.get('redirect_url', url_for('index'))
    response = make_response(redirect(redirect_url))
    if status == 'all' or status == 'necessary':
        response.set_cookie('cookies_accepted', 'true', max_age=3600*24*30)
    else:
        response.set_cookie('cookies_accepted', 'false', max_age=3600*24*30)
    return response


@app.route("/serve_image/<image_name>")
def serve_image(image_name):
    return send_from_directory(
        os.path.join(app.root_path, "static", "images"), image_name
    )

if __name__ == "__main__":
    app.run(debug=True)