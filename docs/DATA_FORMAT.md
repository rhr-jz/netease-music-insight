# 数据格式

`music_for_ai.json` 是 UTF-8 JSON。顶层字段：

- `export_meta`：导出时间、来源、`complete` 或 `partial` 状态、问题清单与播放历史限制。
- `user_profile`：UID 和昵称。
- `liked_songs`：喜欢歌曲，每首含 ID、名称、歌手、专辑与时长。
- `playlists`：歌单元数据、是否自建、接口标称曲目数和可获取的 `tracks`。歌单之间允许出现相同歌曲。
- `song_catalog`：按歌曲 ID 去重后的歌曲，每首含 `liked` 和 `playlist_ids`，因此去重不会抹掉歌单关系。
- `play_history`：当前接口可返回的歌曲、`play_count` 与 `score`。并非逐次播放流水，也不代表完整终身历史。
- `statistics`：客观数量、喜欢歌曲中的高频歌手/专辑，以及可获取播放记录按播放次数汇总的高频歌手。

歌曲 ID 按网易云 ID 去重。相同曲名的不同版本若 ID 不同，会保留为不同歌曲。`track_count` 是歌单接口提供的标称数量，`len(tracks)` 是成功写入的数量；两者可能因下架或权限不同。`liked_song_expected` 是喜欢接口返回的 ID 数量，也可能包含无法获取详情的歌曲。

`raw/` 保留喜欢歌曲 ID 和歌单列表，供本人核对。所有这些文件都可能包含敏感的个人喜好，不要直接提交到公开仓库。
