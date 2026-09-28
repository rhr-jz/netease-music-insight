"""Stable failure categories exposed to user interfaces."""


class MusicInsightError(RuntimeError):
    code = "export_failed"


class LoginFailure(MusicInsightError):
    code = "login_failed"


class NetworkUnavailable(MusicInsightError):
    code = "network_unavailable"


class ProviderUnavailable(MusicInsightError):
    code = "provider_unavailable"


class PlaylistUnavailable(MusicInsightError):
    code = "playlist_unavailable"


class ExportFailed(MusicInsightError):
    code = "export_failed"


class ExportCancelled(MusicInsightError):
    code = "export_cancelled"
