function apply_tablerow_shortcuts(row) {
  row.addEventListener('keydown', (e) => {
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
    }else if (e.keyCode == 37 || e.keyCode == 39) { // <- or ->, seek video +-5 sec
      delta_seek( (e.keyCode - 38)*5 );
    } else if (e.keyCode == 40 || e.keyCode == 38 || e.keyCode == 9) { // down or up

      let current_row = e.target.closest("tr.item");
      let delta = e.keyCode == 40 || (e.keyCode == 9 && !e.shiftKey) ? 1 : -1;
      let target_row = adjacent_row(current_row, delta);
      //console.log(target_row);

      if (target_row != current_row) { // there are more rows
        if (e.target.type != "time" && e.keyCode != 9)  { // next row if not Tab key
          target_row.querySelector("td.name input").focus();
        }
      } else { // no more rows
        if (e.keyCode != 38 && !(e.keyCode == 9 && e.shiftKey) ) { // not arrow up and not shift+Tab
          let name   = current_row.querySelector("input.name");
          let artist = current_row.querySelector("input.artist");

          if (name.value != "" && artist.value != "" && artist == document.activeElement) {
            if (e.keyCode == 9) e.preventDefault();

            let newone = insert_row(current_row.closest("tbody"), -1, 0, 0);
            newone.querySelector("td.name input").focus();
          }
        }
      } // end of no more rows
    }
  });
}

let state = {last_timeout: undefined, is_composing: undefined, last_value: ""};
function extract_word(e) {
  state.is_composing = e.isComposing;
  if (!e.target.value) return;

  if (state.last_timeout !== undefined) {
    clearTimeout(state.last_timeout);
  }

  //console.log(e.target.value, e.isComposing);

  state.last_timeout = setTimeout(()=>{
    if (!state.is_composing) { // safe to overwrite value
      let ext = extractWord(e.target.value, document.querySelector('#search > div').innerHTML);

      // For the case ext is too long (e.g. "坂本真綾の曲")
      if (state.last_value.includes(e.target.value) && e.target.value.length < state.last_value.length) {
        state.last_value = e.target.value;
        return;
      }

      if (ext.includes(e.target.value)) {
        e.target.value = ext;
        state.last_value = ext;
      }
    }
    state.last_timeout = undefined;
  }, 1000);
}

// apply current yt time to time input
function touchend(e) {
  if (player) e.target.value = to_time(player.getCurrentTime());
  timechange(e, false); // no seek
}



// time utils

// update length of segment
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

// seek and apply current time to timeinput
function timeinput_keyup(e) {
  if (!player) return;

  if (e.key == "a") { // apply current time
    touchend(e);
  } else if (e.key == "s") { // seek to time
    seek_to({target: e.target.parentElement}); // for seek_to(e) that looks parent -> child to find time input
  }
}



// youtube

function seek_to(e) {
  let sec = to_num(e.target.closest(".time").querySelector("input.time").value);
  //console.log("seek_to", {sec});
  if (player) {
    player.seekTo(sec);
    player.playVideo();
  }
}

function delta_seek(delta) {
  if (player) {
    let cur = player.getCurrentTime();
    player.seekTo(cur+delta);
  }
}

function yt_toggle(e) {
  if (player) {
    let st = player.getPlayerState();
    if (st == YT.PlayerState.PLAYING || st == YT.PlayerState.BUFFERING) {
      player.pauseVideo();
    } else {
      player.playVideo();
    }
  }
}



function load_segments(txt) {
  let table = document.querySelector("#stamps");
  if ( table.rows.length > 0 && !confirm("すでに読み込み済みです。\n上書きしますか?") )
    return;

  for (;table.rows[0];)
    table.deleteRow(0);

  let text = txt;
  if (text === undefined) text = document.querySelector("#raw_times_input").value;

  text
    .split("\n")
    .forEach((row,i)=>{

      const num_reg = /(\d|\.)+/g;
      let times = [...row.matchAll(num_reg)].map(m=>parseInt(m[0]));
      let others = row.split(/(?<![a-z])\s+(?![a-z])/i)
        .map(el=>el.trim())
        .filter(el=>el && !el.match(num_reg));

      if (times.length == 1)
        times.push(times[0] + 3*60.0);

      let new_row = insert_row(table, i, ...times.slice(0, 2), others[0]||"", others[1]||"");
      apply_tablerow_shortcuts(new_row);

    });
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

  if (is_mobile_html())
    toggle_info(false); // close info pane
}

function search_button(e) {
  search(e.target.parentElement.querySelector("input").value);
}

function upload_tags(e) {

  let table = document.querySelector("#stamps");
  let ar = Array.from(table.rows)
    .map(row => {
      let name = row.querySelector("input.name").value;
      let artist = row.querySelector("input.artist").value;

      //if (!name && !artist) { return ""; } // should save raw data?

      let times = Array.from(row.querySelectorAll("input.time"))
        .map(time_input=>to_num(time_input.value))
        .sort((l,r)=>l-r)
        .map(n=>to_time(n))

      return [...times, name||"", artist||""]
    }); // should save raw data?
    //.filter(row=>row[2] || row[3]);


  // send
  let socket = new WebSocket(`ws://${location.host}/websocket`);
  socket.onopen = function(e) {
    socket.send(
      JSON.stringify({tags: ar, video_id: url2id(document.querySelector("#video_url").value), key: lock}) );
  };

  let timeout_id = setTimeout(()=>{
    socket.close();
    alert("アップロードがタイムアウトしました");
  }, 5*1000);

  socket.onmessage = function(event) {
    clearTimeout(timeout_id);
    let num = parseInt(event.data);
    if (num == ar.length) {
      alert("アップロード完了");

      // unlock
      onclose();

    } else {
      alert(`Error: ${event.data}`);
    }

    socket.close();
  };
}

function show_output(e) {
  let table = document.querySelector("#stamps");
  let text = Array.from(table.rows)
    .map(row => {
      let name = row.querySelector("input.name").value;
      let artist = row.querySelector("input.artist").value;

      if (!name && !artist) { return ""; }

      let times = Array.from(row.querySelectorAll("input.time"))
        .map(time_input=>to_num(time_input.value))
        .sort((l,r)=>l-r)
        .map(n=>to_time(n))
        .join(" - ");

      return `${times} ${name} / ${artist}`;
    })
    .filter(row=>row)
    .join("\n");

  document.querySelector("#tags").textContent = text;
  console.log(text);
}


// For info pane toggle

let moving = false;
function info_move(e) {
  moving = true;
}

function info_toggle(e) {
  if (!moving) {
    let i = e.currentTarget.querySelector("i")
    let to_expand = i.getAttribute("class").match(/up/i);
    let info = e.target.closest("#info");

    toggle_info(to_expand, info, i);
  } else {
    moving = false;
  }
}

function add_item(e) {
  let table = document.querySelector("#stamps");
  let time = (player?.getCurrentTime() || 0);
  let newone = insert_row(table, -1, time, time);

  if (time !== 0)
    sort_item();

  let y = newone.getBoundingClientRect().bottom;
  table.closest("#segments_content").scrollBy(0, y);
}

function delete_item_handle(e) {
  try{
    if (confirm("選択した項目を削除します")) {
      delete_item(e);
    }
  } catch (e) {
    display_pane(`<h2>${e}</h2>\n${ e.stack.split("\n").map(el=> el+"</br>") }`);
  }
}
