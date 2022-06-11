require 'yaml'
require 'json'
require 'pathname'
require 'uri'
require 'net/http'
require 'date'

require 'test/unit'
require 'pp'

require_relative '../ruby/utils'

######################################
#### RUN test/server.rb FIRST!!!! ####
######################################

Utils::DATA_DIR = Pathname("test") / Utils::DATA_DIR


class ServerTest < Test::Unit::TestCase
  self.test_order = :defined
  SELF=self

  LIST_YAML = "list.yaml"

  class << self
    attr_accessor :list_yaml, :cache

    def get(uri, params = {})
      uri = URI("http://#{uri}")
      uri.query = URI.encode_www_form(params)

      res = Net::HTTP.get_response(uri)
      return res.body if res.is_a?(Net::HTTPSuccess)

      puts res.body
      return ""
    end

    def post(uri, json)
			uri = URI.parse("http://#{uri}")

			http = Net::HTTP.new(uri.host, uri.port)

			req = Net::HTTP::Post.new(uri.request_uri)
			req["Content-Type"] = "application/json"

			req.body = json

			res = http.request(req)

			p res.code, res.msg
			return res.body
		rescue => e
			p e.message
    end

    def startup 
      Utils.init()
      SELF.cache = {}
      system("rm -rf #{Utils::DATA_DIR}") if Utils::DATA_DIR.exist?
      system("cp -r #{Utils::DATA_DIR}.model/ #{Utils::DATA_DIR}")

      @list_yaml = YAML.unsafe_load_file(Utils::DATA_DIR / LIST_YAML).map{|item| Utils.decode_videoinfo(item)}
      sleep 0.5
      get("localhost:8001/restart")
    rescue Errno::ECONNREFUSED, EOFError => ex
      puts "Server restarted"
    ensure
      puts "Start #{self}"
    end
    
    def shutdown
      puts "End #{self}"
    end

    def compare_item(&block)
      %i[title video_id published_at duration].each{|k|
        block.call(k)
      }
    end
  end


  test "Get remaining video1" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process"), symbolize_names: true )

    existing = SELF.list_yaml[1]
    SELF.compare_item{|k|
      assert_equal(existing[k].class, v2p[k].class)
      assert_not_equal(existing[k],   v2p[k])
    }

    @@video1 = v2p
    puts "First is #{@@video1[:title]}"
  end

  test "Get remaining video and lock1" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process", {lock: 1}), symbolize_names: true )

    existing = SELF.list_yaml[1]
    SELF.compare_item{|k|
      assert_equal(existing[k].class, v2p[k].class)
      assert_not_equal(existing[k],   v2p[k])
    }

    sleep 0.1

    locked = JSON.parse( SELF.get("localhost:8001/locked"), symbolize_names: true )
    assert_equal(1, locked.size)

    l1 = locked.first
    SELF.compare_item{|k|
      assert_equal(v2p[k],   l1[k])
    }
    @@lock1 = l1
    puts "lock1 is #{@@lock1[:title]}"
  end

  test "Get remaining video2" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process"), symbolize_names: true )

    existing = SELF.list_yaml[1]
    SELF.compare_item{|k|
      assert_equal(existing[k].class,    v2p[k].class)
      assert_not_equal(existing[k],      v2p[k])
      assert_not_equal(@@video1[k], v2p[k])
    }

    @@video2 = v2p
    puts "Second is #{@@video2[:title]}"
  end

  test "Get remaining video and lock2" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process", {lock: 1}), symbolize_names: true )

    existing = SELF.list_yaml[1]
    SELF.compare_item{|k|
      assert_equal(existing[k].class,    v2p[k].class)
      assert_not_equal(existing[k],      v2p[k])
      assert_not_equal(@@video1[k], v2p[k])
    }

    sleep 0.1

    locked = JSON.parse( SELF.get("localhost:8001/locked"), symbolize_names: true )
    assert_equal(2, locked.size)

    @@lock2 = locked.last
    SELF.compare_item{|k|
      assert_equal(v2p[k],   @@lock2[k])
      assert_equal(locked.first[k],   @@lock1[k])
    }
    puts "lock2 is #{@@lock2[:title]}"
  end

  test "Get remaining video3 should empty" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process"), symbolize_names: true )

    assert(v2p.empty?)
    puts "Third is #{v2p}"
  end

  test "Post video1" do
    SELF.post("localhost:8001/segments", {video_id: @@video1[:video_id], segments: "1\t2\n2\t3"}.to_json)

    sleep 0.1

    locked = JSON.parse( SELF.get("localhost:8001/locked"), symbolize_names: true )
    assert_equal(1, locked.size)

    l = locked.first
    SELF.compare_item{|k|
      assert_equal(@@video2[k], l[k])
    }
    puts "remaining lock is #{l[:title]}"
  end

  test "Post video2" do
    SELF.post("localhost:8001/segments", {video_id: @@video2[:video_id], segments: "1\t2\n2\t3"}.to_json)

    sleep 0.1

    locked = JSON.parse( SELF.get("localhost:8001/locked"), symbolize_names: true )
    assert_equal(0, locked.size)

    puts "remaining lock is 0"
  end
 
  test "No remaining" do
    v2p = JSON.parse( SELF.get("localhost:8001/video2process"), symbolize_names: true )

    assert(v2p.empty?)
  end


  #assert_nil(c.block)
end
