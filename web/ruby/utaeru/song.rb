class Song < Hash

  def initialize(name, artist, vid, start_time, end_time)
    self[:name] = name
    self[:artist] = artist
    self[:video_id] = vid
    self[:start_time] = start_time
    self[:end_time] = end_time
  end

end
