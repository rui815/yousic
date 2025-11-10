from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SongShare
from .serializers import SongShareSerializer
from accounts.models import CustomUser # フォロー関係の取得に利用

# Spotify APIライブラリ (例: spotipy)
# (事前に `pip install spotipy` が必要)
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.utils import timezone
import os # ★ .env から読み込むために os をインポート
from datetime import timedelta # ★ 有効期限の計算に必要

# ----------------------------------------------------
# ★ Spotify API 関連のロジック（ヘルパー関数）
# ----------------------------------------------------
# (これはviews.py内、または別のspotify_utils.pyファイルに記述します)

def get_spotify_api_client(user):
    """
    ユーザーのトークンを使ってSpotipyクライアントを取得します。
    トークンが切れていたらリフレッシュします。
    """
    
    # 1. .env から Spotify アプリケーションの認証情報を読み込む
    #    (settings.pyで load_dotenv() 済み)
    CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI') # リフレッシュ時にも必要

    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        # サーバー側で環境変数が設定されていない場合
        print("サーバーエラー: Spotifyの環境変数 (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI) が設定されていません。")
        return None

    # 2. ユーザーのDBにトークンが保存されているか確認
    if not user.spotify_refresh_token or not user.spotify_access_token:
        # Swift側での初回認証がまだ
        print(f"ユーザー {user.username} はSpotifyの初回認証が完了していません。")
        return None
        
    # 3. トークンが期限切れかチェック
    token_expired = False
    if user.spotify_token_expires_at and user.spotify_token_expires_at < timezone.now():
        token_expired = True

    try:
        if token_expired:
            # --- 4. トークンリフレッシュ処理 ---
            print(f"ユーザー {user.username} のトークンが期限切れです。リフレッシュします...")
            
            # spotipyのOAuthハンドラを初期化
            # (scope は client_auth.py と同じものを指定)
            sp_oauth = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope="user-read-currently-playing user-read-recently-played"
            )
            
            # リフレッシュトークンを使って新しいアクセストークンを取得
            new_token_info = sp_oauth.refresh_access_token(user.spotify_refresh_token)
            
            # 5. 新しいトークン情報をDBに保存
            user.spotify_access_token = new_token_info['access_token']
            # (expires_in から expires_at を計算して保存)
            user.spotify_token_expires_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
            
            # Spotifyはリフレッシュ時に新しいリフレッシュトークンを返すことがある
            if 'refresh_token' in new_token_info and new_token_info['refresh_token']:
                user.spotify_refresh_token = new_token_info['refresh_token']
                
            user.save()
            print(f"ユーザー {user.username} のトークンをリフレッシュしました。")

        # 6. 有効なアクセストークンでSpotipyクライアントを初期化
        return spotipy.Spotify(auth=user.spotify_access_token)

    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify APIエラー (リフレッシュ失敗など): {e}")
        # リフレッシュに失敗した場合、ユーザーは再認証が必要
        return None
    except Exception as e:
        print(f"トークンリフレッシュ中の予期せぬエラー: {e}")
        return None
    
# ----------------------------------------------------
# API ビュー
# ----------------------------------------------------

class ShareCurrentSongView(APIView):
    """
    POST: 現在再生中の曲を取得し、SongShareとしてデータベースに保存します。
    (BeRealの通知に応じてSwiftアプリから叩かれるAPI)
    """
    permission_classes = [permissions.IsAuthenticated] # 認証必須

    def post(self, request, *args, **kwargs):
        user = request.user

        # 1. Spotify APIクライアントを取得 (トークンリフレッシュ含む)
        sp = get_spotify_api_client(user)

        if not sp:
            return Response(
                {"detail": "Spotify authentication required or token refresh failed."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            # 2. Spotify APIから「今聞いている曲」を取得
            current_track = sp.current_user_playing_track()

            if not current_track or not current_track.get('item'):
                return Response({"detail": "No track is currently playing."}, status=status.HTTP_404_NOT_FOUND)

            track_info = current_track['item']

            # 3. 取得した曲をデータベースに保存
            # (既に同じ曲を直近でシェアしていないか等のチェックもここに入れられる)
            song_share = SongShare.objects.create(
                user=user,
                spotify_track_id=track_info['id'],
                track_name=track_info['name'],
                artist_name=', '.join([artist['name'] for artist in track_info['artists']]), # 複数のアーティストを考慮
                album_cover_url=track_info['album']['images'][0]['url'] if track_info['album']['images'] else None # 簡略化
            )
            
            serializer = SongShareSerializer(song_share)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except spotipy.exceptions.SpotifyException as e:
            # (例: APIレート制限、認証エラーなど)
            return Response({"detail": f"Spotify API Error: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An unexpected error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FollowingFeedView(generics.ListAPIView):
    """
    GET: 自分がフォローしているユーザーのSongShare一覧（フィード）を取得します。
    """
    serializer_class = SongShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # 1. 自分がフォローしているユーザーのIDリストを取得
        # (CustomUserのrelated_name='follower_set'を利用)
        following_users_qs = CustomUser.objects.filter(follower_set__follower=user)
        
        # 2. そのユーザーたちのSongShareを日付順（新しい順）に取得
        # (SongShareのMeta.orderingで既に'-shared_at'が指定されているが、明示も可能)
        queryset = SongShare.objects.filter(user__in=following_users_qs)
        
        return queryset
