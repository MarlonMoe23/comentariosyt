import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
from googleapiclient.discovery import build
import re
from dotenv import load_dotenv
import os

# Cargar la API KEY del archivo .env
load_dotenv()
api_key = os.getenv('API_KEY')

# Inicializar la app Dash
app = dash.Dash(__name__)

# Estilos CSS personalizados
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
    /* Estilos generales */
    .responsive-table-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    /* Estilos para la tabla */
    .responsive-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }

    .responsive-table th,
    .responsive-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
        min-width: 100px;
    }

    .responsive-table th {
        background-color: #f4f4f4;
        font-weight: bold;
    }

    /* Estilos para móviles */
    @media screen and (max-width: 600px) {
        .responsive-table thead {
            display: none;
        }
        .responsive-table {
            display: block;
        }
        .responsive-table tbody,
        .responsive-table tr {
            display: block;
        }
        .responsive-table td {
            display: flex;
            align-items: flex-start;
            padding: 8px;
            border: none;
            white-space: normal;
            word-break: break-word;
        }
        .responsive-table td::before {
            content: attr(data-label);
            font-weight: bold;
            width: 120px;
            min-width: 120px;
            margin-right: 8px;
        }
        .responsive-table td[data-label="Comentario"] {
            flex-direction: column;
            align-items: flex-start;
            white-space: normal;
            word-break: break-word;
            padding-left: 0;
            padding-right: 0;
        }
        .responsive-table td[data-label="Comentario"]::before {
            margin-bottom: 4px;
        }
        .responsive-table tr {
            margin-bottom: 15px;
            border-bottom: 2px solid #ddd;
        }
    }
</style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout de la app
app.layout = html.Div([
    dcc.Store(id='comments-store'),  # Almacén de datos
    html.H1("Extractor de comentarios de YouTube",
            style={'textAlign': 'center', 'margin': '20px 0', 'fontSize': '24px'}),
    html.Div([
        dcc.Input(
            id="youtube-url",
            type="text",
            placeholder="Tu URL de YouTube",
            style={
                'width': '80%',
                'maxWidth': '500px',
                'padding': '10px',
                'marginRight': '10px',
                'marginBottom': '10px'
            }
        ),
        html.Button(
            'Enviar',
            id='submit-button',
            n_clicks=0,
            style={
                'padding': '10px 20px',
                'backgroundColor': '#4CAF50',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer'
            }
        ),
    ], style={'textAlign': 'center', 'margin': '20px 0'}),
    html.Div([
        html.Button(
            'DESCARGAR COMENTARIOS',
            id='download-button',
            n_clicks=0,
            style={
                'display': 'none',
                'padding': '10px 20px',
                'backgroundColor': '#008CBA',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'margin': '10px 0'
            }
        )
    ], style={'textAlign': 'center'}),
    dcc.Download(id="download-excel"),
    html.Div(id="output-div", style={'padding': '20px'})
], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '0 15px'})

def get_video_id(url):
    """
    Extrae el ID del video de una URL de YouTube en los formatos más comunes.
    """
    # youtu.be/VIDEO_ID
    match = re.match(r'(https?://)?(www\.)?youtu\.be/([^?&]+)', url)
    if match:
        return match.group(3)
    # youtube.com/watch?v=VIDEO_ID (incluye m.youtube.com)
    match = re.match(r'(https?://)?(www\.|m\.)?youtube\.com/watch\?v=([^&]+)', url)
    if match:
        return match.group(3)
    # youtube.com/watch?...&v=VIDEO_ID&...
    match = re.search(r'v=([^&]+)', url)
    if match:
        return match.group(1)
    return None

def get_comments(video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    comments_data = []
    next_page_token = None

    while True:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText"
        )
        response = request.execute()

        for item in response.get('items', []):
            top_comment = item['snippet']['topLevelComment']['snippet']
            main_comment = {
                "Autor": top_comment['authorDisplayName'],
                "Comentario": top_comment['textDisplay'],
                "Likes": top_comment['likeCount'],
                "Publicado en": top_comment['publishedAt'],
                "Es respuesta": "No"
            }
            comments_data.append(main_comment)

            # Agregar respuestas si existen
            replies = item.get('replies', {}).get('comments', [])
            for reply in replies:
                reply_snippet = reply['snippet']
                response_comment = {
                    "Autor": reply_snippet['authorDisplayName'],
                    "Comentario": reply_snippet['textDisplay'],
                    "Likes": reply_snippet['likeCount'],
                    "Publicado en": reply_snippet['publishedAt'],
                    "Es respuesta": "Sí"
                }
                comments_data.append(response_comment)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return comments_data

def create_grouped_table(df):
    rows = []
    for i, row in df.iterrows():
        is_reply = row["Es respuesta"] == "Sí"
        style = {'paddingLeft': '40px'} if is_reply else {'backgroundColor': '#f8f8f8'}

        rows.append(
            html.Tr([
                html.Td(row["Autor"], **{'data-label': 'Autor'}, style=style),
                html.Td(row["Comentario"], **{'data-label': 'Comentario'}, style=style),
                html.Td(row["Likes"], **{'data-label': 'Likes'}, style=style),
                html.Td(row["Publicado en"], **{'data-label': 'Publicado en'}, style=style),
            ])
        )

    table = html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th("Autor"),
                html.Th("Comentario"),
                html.Th("Likes"),
                html.Th("Publicado en")
            ])),
            html.Tbody(rows)
        ], className='responsive-table')
    ], className='responsive-table-container')

    return table

@app.callback(
    Output('output-div', 'children'),
    Output('download-button', 'style'),
    Output('comments-store', 'data'),
    Input('submit-button', 'n_clicks'),
    State('youtube-url', 'value')
)
def update_output(n_clicks, url):
    if n_clicks > 0:
        video_id = get_video_id(url)
        if video_id:
            comments_data = get_comments(video_id)
            df = pd.DataFrame(comments_data)
            grouped_table = create_grouped_table(df)
            button_style = {
                'display': 'inline-block',
                'padding': '10px 20px',
                'backgroundColor': '#008CBA',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'margin': '10px 0'
            }
            return grouped_table, button_style, comments_data
        else:
            return "Link de YouTube inválido", {'display': 'none'}, None
    return "", {'display': 'none'}, None

@app.callback(
    Output('download-excel', 'data'),
    Input('download-button', 'n_clicks'),
    State('comments-store', 'data'),
    State('youtube-url', 'value')
)
def download_comments(n_clicks, stored_comments, url):
    if n_clicks > 0 and stored_comments:
        video_id = get_video_id(url)
        if video_id:
            df = pd.DataFrame(stored_comments)
            output_filename = f"youtube_comments_{video_id}.xlsx"
            return dcc.send_data_frame(df.to_excel, output_filename, index=False)
    return None

server = app.server

if __name__ == '__main__':
    app.run(debug=False)