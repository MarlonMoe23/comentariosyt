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

# Layout de la app
app.layout = html.Div([
    html.H1("Extractor de comentarios de YouTube"),
    html.Div([
        dcc.Input(id="youtube-url", type="text", placeholder="Tu URL de YouTube"),
        html.Button('Enviar', id='submit-button', n_clicks=0),
    ], style={'textAlign': 'center'}),
    html.Div([
        html.Button('DESCARGAR COMENTARIOS', id='download-button', n_clicks=0, style={'display': 'none'})
    ], style={'textAlign': 'center', 'margin': '9, auto'}),
    dcc.Download(id="download-excel"),
    html.Div(id="output-div", style={'textAlign': 'left', 'padding': '20px'}),
])

def get_video_id(url):
    match = re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$', url)
    if match:
        found = re.search(r'v=([^&]+)', url)
        if found:
            return found.group(1)
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
        style = {'paddingLeft': '40px'} if is_reply else {'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'}

        rows.append(
            html.Tr([
                html.Td(row["Autor"], style=style),
                html.Td(row["Comentario"], style=style),
                html.Td(row["Likes"], style=style),
                html.Td(row["Publicado en"], style=style),
            ])
        )

    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Autor"), html.Th("Comentario"), html.Th("Likes"), html.Th("Publicado en")
        ])),
        html.Tbody(rows)
    ], style={'width': '100%', 'borderCollapse': 'collapse'})
    return table

@app.callback(
    Output('output-div', 'children'),
    Output('download-button', 'style'),
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
            return grouped_table, {'display': 'inline-block'}
        else:
            return "Link de YouTube inválido", {'display': 'none'}
    return "", {'display': 'none'}

@app.callback(
    Output('download-excel', 'data'),
    Input('download-button', 'n_clicks'),
    State('youtube-url', 'value')
)
def download_comments(n_clicks, url):
    if n_clicks > 0:
        video_id = get_video_id(url)
        if video_id:
            comments_data = get_comments(video_id)
            df = pd.DataFrame(comments_data)
            output_filename = f"youtube_comments_{video_id}.xlsx"
            return dcc.send_data_frame(df.to_excel, output_filename, index=False)
    return None

if __name__ == '__main__':
    app.run(debug=False)

