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

function to_time(num, digit=3) {
  let date = new Date(0);
  date.setSeconds(num);
  let offset = (3-digit)*3; // 3 is e.g. hh:, mm:
  return date.toISOString().substr(11 + offset, 8-offset);
}

function to_num(time) {
  return time
    .split(":")
    .reverse()
    .map((s,i) => 60**i * parseInt(s))
    .reduce((el, sum)=>el+sum, 0)
}


// For UI

function touchend(e) {
  if (player) e.target.value = to_time(player.getCurrentTime());
  timechange(e, false); // no seek
}

function timeinput_nonPC(time, is_start) {
  let startend = is_start ? "start" : "end";
  let time_input = `
  <div class="time_input">
    <input type="text" class="time ${startend}" value="${time}" onchange="timechange(event);" readonly="readonly" ontouchend="touchend(event);"/>
    <div class="time_buttons">
      <button class="fa-solid fa-minus" onclick="changetime(event, -1)"></button>
      <button class="fa-solid fa-plus"  onclick="changetime(event, +1)"></button>
    </div>
  </div>
`;
  if (is_start) {
    return `
    ${time_input}
    <button class="fa-solid fa-angles-left"></button>`;
  } else {
    return `
    <button class="fa-solid fa-angles-right"></button>
    ${time_input}
    `;
  }
}

function gen_timeinput(value, is_start=true) {
  if (detectMobile()) {
    return timeinput_nonPC(value, is_start);
  } else {
    let startend = is_start ? "start" : "end";
    return `<input type="time" class="time ${startend}" value="${value}" onchange="timechange(event);" />`;
  }
}

function insert_row(table, idx, start, end) {
  let new_row = table.insertRow(-1);
  new_row.setAttribute("class", "item");
  new_row.innerHTML = segment_row(idx, start, end);
  return new_row;
}

function segment_row(idx, start, end) {
  if (is_mobile_html()) {
    return `
<td class="no">${idx}</td>
<td class="item">
<table>
  <tr>
    <td><label class="start">Start time</label></td>
    <td><label class="ldngth">Length</label></td>
    <td><label class="end">End time</label></td>
  </tr>
  <tr>
    <td><div class="time start">${ gen_timeinput(to_time(start)) }</div></td>
    <td><div class="length">${to_time(end-start, 2)}</div></td>
    <td><div class="time end">${   gen_timeinput(to_time(end), false) }</div></td>
  </tr>
</table>
  <div class="name">
    <button class="fa-solid fa-magnifying-glass" onclick="search_button(event)"></button>
    <input type="text" onfocus="on_songname_focus(event);" placeholder="Song name"></input>
  </div>
  <div class="artist"><input type="text" placeholder="Artist"></input></div>
</td>`;
  } else {
    return `
<td class="no">${idx}</td>
<td class="time start">${ gen_timeinput(to_time(start)) }</td>
<td class="time end">${   gen_timeinput(to_time(end), false) }</td>
<td class="length">${to_time(end-start, 2)}</td>
<td class="name">
  <button class="fa-solid fa-magnifying-glass" onclick="search_button(event)"></button>
  <input type="text" onfocus="on_songname_focus(event);"></input>
</td>
<td class="artist"><input type="text"></input></td>`;
  }
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
        let new_row = insert_row(table, i, ...times);
        apply_tablerow_shortcuts(new_row);
      }

    });
}


// time utils
function timechange(e, seek=true) {
  // e.target == input
  let item = e.target.closest(".item");

  let length = item.querySelector(".length");
  let times = Array.from(item.querySelectorAll("input.time"))
    .map(time_input=>to_num(time_input.value))
    .sort((l,r)=>l-r).reverse();

  //console.log(times);
  //console.log(times.map(x=>to_time(x)));

  length.innerText = to_time(times[0]-times[1], 2);

  if (player && seek) player.seekTo(to_num(e.target.value), true);
}

function changetime(e, delta) {
  let cntner = e.target.closest(".time");
  let input = cntner.querySelector("input");
  input.value = to_time(to_num(input.value)+delta);
  timechange({target: input});
}



var focused;
function on_songname_focus(e) {
  if (e.target != focused) {
    let tr = e.target.closest(".item");
    let raw_time = tr.querySelector("input.time.start").value;
    let time = to_num(raw_time);
    focused = e.target;

    console.log(`Start ${raw_time}`);
    if (player !== undefined) {
      player.playVideo();
      player.seekTo(time, true);
    }
  }
}

function update_video(e) {
  let id = url2id(e.target.parentElement.querySelector("input").value);
  console.log(id);

  if (player === undefined) {
    player = load_video(id);
  } else {
    player.loadVideoById(id);
  }
}

function adjacent_row(row, delta) {
  let idx = row.rowIndex + delta -1; // 1 origin?

  if (0 <= idx && idx < row.parentNode.rows.length) {
    return row.parentNode.rows[idx];
  } else {
    return row;
  }
}


// Search
function search(word) {
  console.log(`search got "${word}"`);
  if (word !== "") {
    socket.send(word);
  }
}

function search_button(e) {
  search(e.target.parentElement.querySelector("input").value);
}



function apply_tablerow_shortcuts(row) {
  row.addEventListener('keyup', (e) => {
    //console.log(e.target, `Key "${e.key}" released  [event: keyup]`);

    if (e.target.type != "text" && e.key == " ") { // space key and not text input
      let st = player.getPlayerState();
      if (st == YT.PlayerState.PLAYING) {
        player.pauseVideo();
      } else {
        player.playVideo();
      }
    } else if (e.ctrlKey && e.keyCode == 13) { // Ctrl+Enter -> search word
      search(e.target.value);
    } else if (e.keyCode == 40 || e.keyCode == 38) { // down or up
      //                         td            tr
      let current_row = e.target.parentElement.parentElement
      let target_row = adjacent_row(current_row, e.keyCode - 39);

      if (target_row != current_row) {
        target_row.querySelector("td.name > input").focus();
      }
    }
  });
}

function show_output(e) {
  let table = document.querySelector("#stamps");
  let text = Array.from(table.rows)
    .map(row => {
      let name = row.querySelector("td.name > input[type='text']").value;
      let artist = row.querySelector("td.artist > input[type='text']").value;

      if (!name && !artist) { return ""; }

      let times = Array.from(row.querySelectorAll("td.time > input"))
        .map(time_input=>to_num(time_input.value))
        .sort((l,r)=>l-r)
        .map(n=>to_time(n))
        .join(" - ");

      return `${times} ${name} / ${artist}`;
    })
    .filter(row=>row)
    .join("\n");

  document.querySelector("#output_content > textarea").textContent = text;
  console.log(text);
}


let mobile = undefined;
function detectMobile() {
  if (mobile === undefined) {
    const toMatch = [
           /Android/i,
           /webOS/i,
           /iPhone/i,
           /iPad/i,
           /iPod/i,
           /Safari/i,
           /BlackBerry/i,
           /Windows Phone/i
     ];

     mobile = toMatch.some((toMatchItem) => {
       return navigator.userAgent.match(toMatchItem);
     });
  }

  return mobile;
}

let mobile_html = undefined;
function is_mobile_html() {
  if (mobile_html === undefined) {
    let tbody = document.querySelector("#stamps");
    mobile_html = tbody.parentElement.querySelectorAll("th").length === 2;
  }

  return mobile_html;
}
