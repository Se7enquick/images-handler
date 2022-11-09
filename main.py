import pathlib
import random
import shutil
import string
from datetime import datetime

from fastapi import FastAPI, Form, UploadFile, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, RedirectResponse

BASE_FOLDER = pathlib.Path(__file__).resolve().parent
DATA_FOLDER = BASE_FOLDER / 'data'
DATA_FOLDER.mkdir(exist_ok=True)

CONFIG_FILENAME = 'config.txt'
RESULTS_FILENAME = 'results.zip'

app = FastAPI(debug=True)

templates = Jinja2Templates(directory="templates")

AVAILABLE_PROCESS_METHODS = {
    'remove_gray': 'Remove gray',
    'remove_blur': 'Remove blur'
}


@app.get('/')
def index(request: Request):
    return templates.TemplateResponse("index.html", context={
        'request': request,
        'processing_methods': AVAILABLE_PROCESS_METHODS
    })


@app.post('/')
def start_processing(request: Request, images_zip_file: UploadFile, config_file: UploadFile,
                     background_tasks: BackgroundTasks, process_method: str = Form()):
    # assert images_zip.content_type == 'application/zip'

    folder_name = generate_folder_name()
    folder = DATA_FOLDER / folder_name
    folder.mkdir()

    save_file(folder, images_zip_file, filename=images_zip_file.filename)
    save_file(folder, config_file, filename=CONFIG_FILENAME)

    background_tasks.add_task(process_zip, images_path=folder / images_zip_file.filename, method=process_method)

    full_domain = get_full_domain(request)
    download_path = app.url_path_for('download_results', folder_name=folder.name)

    return templates.TemplateResponse("success_page.html", context={
        'request': request,
        'result_url': f'{full_domain}{download_path}'
    })


@app.get('/download/{folder_name}')
def download_results(folder_name: str):
    results_file = DATA_FOLDER / folder_name / RESULTS_FILENAME
    if not results_file.exists():
        return RedirectResponse(app.url_path_for('results_does_not_exist'))

    return FileResponse(results_file)


@app.get('/results_does_not_exist')
def results_does_not_exist(request: Request):
    return templates.TemplateResponse("results_file_does_not_exist.html", context={'request': request})


def get_full_domain(request: Request):
    schema, rest = str(request.url).split('//')
    domain, _ = rest.split('/', 1)

    return f'{schema}//{domain}'


def generate_folder_name() -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    return f'{timestamp}_{suffix}'


def save_file(folder: pathlib.Path, upload_file: UploadFile, filename: str):
    with (folder / filename).open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def process_zip(images_path: pathlib.Path, method: str):
    folder = images_path.parent

    config_path = folder / CONFIG_FILENAME
    result_path = folder / RESULTS_FILENAME

    # TODO: use method
