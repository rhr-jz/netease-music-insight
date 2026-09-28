# 数据格式

`music_for_ai.json` 是 UTF-8 JSON。顶层字段：

网易云与 QQ 音乐各自生成此文件；联合输出为 `music_for_ai_combined.json`，保留两平台的原始分析结构并附高置信匹配目录。

- `export_meta`：导出时间、来源、`complete` 或 `partial` 状态、问题清单与播放历史限制。
- `user_profile`：UID 和昵称。
- `liked_songs`：喜欢歌曲，每首含平台 ID、名称、歌手、专辑、时长及可用时的 `liked_at`。QQ 同时保留 songid 和 songmid。
- `playlists`：歌单元数据、是否自建、接口标称曲目数、可获取的 `tracks`，以及接口提供的 `created_at`、`subscribed_at` 或 `favorite_order_at`。QQ 的 `favorite_order_at` 是收藏排序时间，不保证等于首次收藏日期。
- `song_catalog`：按歌曲 ID 去重后的歌曲，每首含 `liked` 和 `playlist_ids`，因此去重不会抹掉歌单关系。
- `play_history`：网易云当前接口可返回的歌曲、`play_count` 与 `score`。并非逐次播放流水，也不代表完整终身历史。QQ 音乐当前为空，`data_availability` 标出原因。
- `statistics`：客观数量、喜欢歌曲中的高频歌手/专辑，以及可获取播放记录按播放次数汇总的高频歌手。

单平台歌曲按该平台 ID 去重。联合数据仅在标题、歌手集合和时长唯一匹配时自动合并；Live 等版本不会因相似名称合并。`track_count` 是歌单接口提供的标称数量，`len(tracks)` 是成功写入的数量；两者可能因下架或权限不同。`liked_song_expected` 是喜欢接口返回的数量，也可能包含无法获取详情的歌曲。

网易云 `raw/` 保留喜欢歌曲 ID 和歌单列表，供本人核对。所有这些文件都可能包含敏感的个人喜好，不要直接提交到公开仓库。
