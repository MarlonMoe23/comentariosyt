import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
from googleapiclient.discovery import build
import re
from dotenv import load_dotenv
import os

# Load the API KEY from the .env file
load_dotenv()
api_key = os.getenv('API_KEY')

# Initialize the Dash app
app = dash.Dash(__name__)

# Create the layout for the page
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
    html.Div(id="output-div", style={'textAlign': 'center'}),
])

def get_video_id(url):
    video_id = None
    match = re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$', url)
    if match:
        video_id = re.search(r'v=([^&]+)', url).group(1)
    return video_id

def get_comments(video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=1000
    )
    response = request.execute()
    
    comments_data = []
    for item in response['items']:
        comment = item['snippet']['topLevelComment']['snippet']
        comments_data.append({
            "Autor": comment['authorDisplayName'],
            "Comentario": comment['textDisplay'],
            "Likes": comment['likeCount'],
            "Publicado en": comment['publishedAt']
        })
    return comments_data

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
            print(df)
            table = html.Table([
                html.Thead(
                    html.Tr([html.Th(col) for col in df.columns])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(df.iloc[i][col]) for col in df.columns
                    ]) for i in range(len(df))
                ])
            ])
            return table, {'display': 'inline-block'}
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
    app.run_server(debug=False)
