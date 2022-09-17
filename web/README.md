# Songname quick tagger

## modify source

https://redmine.lighttpd.net/boards/2/topics/9812
```bash
~/services/SongRecog/web/vendor/bundle/ruby/2.7.0/gems/em-websocket-0.3.8/lib/em-websocket/handler_factory.rb:73
> unless request['connection'] && request['connection'] =~ /Upgrade/i 
```

## Production
```bash
APP_ENV=production bundle exec ruby server.rb -l data/list.yaml

```

For tag comments
```bash
APP_ENV=production bundle exec ruby server.rb -l data/list.yaml --lc data/comments/data.yaml -s "google sheet id and gid"
```

## Develop
```bash
APP_ENV=development bundle exec ruby test/server.rb
```

## Export for vsonglister
```bash
bundle exec ruby ruby/export.rb data/ y gsheet_gen/data/UCopMhlXMdVAQOWQhDCdqQmw/
```

## get videos in a list
```bash
bundle exec ./bin/get_list.rb data/list.yaml (cat /path/to/apikey.txt) "play_list_id"
```

## get videos with comments and description
```bash
bundle exec bin/filter_videos.rb data/comments/data.yaml (cat /path/to/apikey.txt) "play_list_id" "0..20"
