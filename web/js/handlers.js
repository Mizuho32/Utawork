function touchend(e) {
  if (player) e.target.value = to_time(player.getCurrentTime());
  timechange(e, false); // no seek
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

function seek_to(e) {
  let sec = to_num(e.target.closest(".time").querySelector("input.time").value);
  //console.log("seek_to", {sec});
  if (player) {
    player.seekTo(sec);
    player.playVideo();
  }
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

function search_button(e) {
  search(e.target.parentElement.querySelector("input").value);
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

  document.querySelector("#output_content > textarea").textContent = text;
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
  let newone = insert_row(table, -1, 0, 0);
  let y = newone.getBoundingClientRect().bottom;
  table.closest("#segments_content").scrollBy(0, y);
}

function delete_item_handle(e) {
  if (confirm("選択した項目を削除します")) {
    delete_item(e);
  }
}
