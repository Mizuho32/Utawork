function url2id(url) {

  if (url.includes("youtube")) {
    return url.match(/v=([^=&]+)/)[1]
  }

  return url; // looks id
}

// 4. The API will call this function when the video player is ready.
function onPlayerReady(event) {
  /*event.target.playVideo();*/
}

// 5. The API calls this function when the player's state changes.
//    The function indicates that when playing a video (state=1),
//    the player should play for six seconds and then stop.
var done = false;
function onPlayerStateChange(event) {
  //if (event.data == YT.PlayerState.PLAYING && !done) {
  //  setTimeout(stopVideo, 6000);
  //  done = true;
  //}
}

function load_video(id) {
  console.log(`load video ${id}`);
  return new YT.Player('player', {
    /*height: '360',
    width: '640',*/
    videoId: id,
    events: {
      'onReady': onPlayerReady,
      'onStateChange': onPlayerStateChange
    }
  })
}

function to_time(num) {
  let date = new Date(0);
  date.setSeconds(num);
  return date.toISOString().substr(11, 8);
}

function to_num(time) {
  return time
    .split(":")
    .reverse()
    .map((s,i) => 60**i * parseInt(s))
    .reduce((el, sum)=>el+sum, 0)
}

function segment_row(idx, start, end) {
  return `
<td class="no">${idx}</td>
<td class="time start"><input type="time" value="${to_time(start)}" onchange="timechange(event);" /></th>
<td class="time end"><input type="time" value="${to_time(end)}" onchange="timechange(event);" /></th>
<td class="length">${to_time(end-start)}</th>
<td class="name"><input type="text" onfocus="on_songname_focus(event);"></input></th>
<td class="artist"><input type="text"></input></th>`;
}

function load_segments() {
  let table = document.querySelector("#stamps");
  for (;table.rows[0];)
    table.deleteRow(0);

  let area = document.querySelector("#raw_times_input");
  area.value
    .split("\n")
    .forEach((row,i)=>{

      let times = row.split(/\s+/).map(n=>parseInt(n));
      if (times.length == 2) {
        let row_html = segment_row(i, ...times);

        let new_row = table.insertRow(-1);
        new_row.innerHTML = row_html;
        apply_tablerow_shortcuts(new_row);
      }

    });
}

function timechange(e) {
  let tr = e.target.parentElement.parentElement;

  let length = tr.querySelector("td.length");
  let times = Array.from(tr.querySelectorAll("td.time > input"))
    .map(time_input=>to_num(time_input.value))
    .sort((l,r)=>l-r).reverse();

  //console.log(times);
  //console.log(times.map(x=>to_time(x)));

  length.innerText = to_time(times[0]-times[1]);

  player.seekTo(Math.min(...times), true);
}

function on_songname_focus(e) {
  let tr = e.target.parentElement.parentElement;
  let raw_time = tr.querySelector("td.time.start > input").value;
  let time = to_num(raw_time);

  console.log(`Start ${raw_time}`);
  console.log(player);

  player.playVideo();
  player.seekTo(time, true);
}

function update_video(e) {
  let id = url2id(e.target.parentElement.querySelector("input").value);
  console.log(id);
  
  player.loadVideoById(id);
}

function apply_tablerow_shortcuts(row) {
  row.addEventListener('keyup', (e) => {
    //console.log(e.target, `Key "${e.key}" released  [event: keyup]`);

    if (e.target.type != "text" && e.key == " ") { // space key
      let st = player.getPlayerState();
      if (st == YT.PlayerState.PLAYING) {
        player.pauseVideo();
      } else {
        player.playVideo();
      }
    } else if (e.ctrlKey && e.keyCode == 13) { // Ctrl+Enter
      socket.send(e.target.value);      
    }
  });
}
