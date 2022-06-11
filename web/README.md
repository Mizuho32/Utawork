# Songname quick tagger

## modify source

https://redmine.lighttpd.net/boards/2/topics/9812
```bash
~/services/SongRecog/web/vendor/bundle/ruby/2.7.0/gems/em-websocket-0.3.8/lib/em-websocket/handler_factory.rb:73
> unless request['connection'] && request['connection'] =~ /Upgrade/i 
```

## Develop
```bash
APP_ENV=development bundle exec ruby test/server.rb
```
