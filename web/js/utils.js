function url2id(url) {

  if (url.includes("youtu")) {
    return url.match(/(?:v=|\.be\/)([^=&\/]+)/i)[1]
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
  let rect = document.querySelector("#player_container").getBoundingClientRect();
  let width  = rect.width;
  let height = rect.height;
  return new YT.Player('player', {
    height: String(height),
    width:  String(width),
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
  let splitten = time.split(":")
  if (splitten.length == 2) // Chrome && second == 0
    splitten.push("00");

  return splitten
    .reverse()
    .map((s,i) => 60**i * parseInt(s))
    .reduce((el, sum)=>el+sum, 0)
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
    let socket = new WebSocket(`ws://${location.host}/websocket`);

    socket.onopen = function(e) {
      socket.send(JSON.stringify({search: word}));
    };

    socket.onmessage = function(event) {
      display_pane(event.data, (div) =>{
        div.querySelectorAll("a").forEach(a=>{
          a.removeAttribute("href");
          a.setAttribute("tabindex", "-1");
        });
      });

      if (is_mobile_html()) toggle_info(true);
      socket.close();
    };

  }
}

function display_pane(html, postprocess) {
  let div = document.querySelector('#search > div')
  div.innerHTML = html;
  if (postprocess) postprocess(div);
  if (is_mobile_html()) toggle_info(true);
}

function escapeRegex(string) {
      return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

function extractWord(word, html) {
  if (!word) return word;

  let initial = html.indexOf(word);
  let subst = html.substring(initial-50, initial-1) + html.substring(initial, initial+50);
  let nonsymbols = "[^-!$%^&*()_+|~=\`{}\\[\\]:\\\";'<>?,.\\/ ]";
  //console.log({word, initial, subst});

  return subst.match(`(${nonsymbols}*${escapeRegex(word)}${nonsymbols}*)`)?.[1] || "";
}



// mobile judge
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

    let to_match = toMatch.some((toMatchItem) => {
      return navigator.userAgent.match(toMatchItem);
    });
    let windows = navigator.userAgent.match(/Windows/i);
    let linux   = navigator.userAgent.match(/Linux/i);

    if (to_match) {
      if (linux || (!linux && !windows) ) // Android or iOS
        mobile = true;
      else
        mobile = false;
    } else {
        mobile = false;
    }

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


function toggle_info(open, info, i) {
  if (!info) info = document.querySelector("#info");
  if (!i) i = info.querySelector("i");

  setTimeout(()=>{
    if (open) {
      info.style.top    = "10%";
      info.style.height = "90%";
      i.setAttribute("class", "fa-solid fa-angles-down");
    } else {
      info.style.top    = "";
      info.style.height = "";
      i.setAttribute("class", "fa-solid fa-angles-up");
    }
  }, 150);
}


function delete_item(e) {
    let table = document.querySelector("#stamps");
    let deletes = [];
    for (let i=0, row; row = table.rows[i]; i++){
      if (row.querySelector("input[type='checkbox']").checked) {
        //console.log("delete", row);
        deletes.push(row);
      }
    }
    deletes.reverse().forEach(row=>row.remove());

    sort_item();
}

function sort_item() {
  let table = document.querySelector("#stamps");
  let slctr = "input.time.start";

  Array.from(table.rows)
    .sort((l,r) => to_num(l.querySelector(slctr).value) - to_num(r.querySelector(slctr).value))
    .map((row,i)=>{
      row.querySelector("td.no  label").innerHTML = String(i);
      return row;
    })
    .forEach(tr=>table.appendChild(tr));
}


function isInvalidDate(date) {
  return Number.isNaN(date.getTime());
}

// url -> lock, already_locked?
function get_lock(url) {
  let l = url.searchParams.get("lock");
  console.log({l}, !!l);

  if (!l) { // no lock
    return [(new Date()).toISOString(), false];
  } else {
    let d = new Date(l);
    if (isInvalidDate(d)) { // invalid lock
      return [(new Date()).toISOString(), false];
    } else {
      return [d.toISOString(), true];
    }
  }
}

function ws_ensure(onopen, onmessage, ontimeout, timeout) {
  // send
  let socket = new WebSocket(`ws://${location.host}/websocket`);
  socket.onopen = function(e) {
    onopen(socket, e);
  };

  let timeout_id = setTimeout(()=>{
    ontimeout();
    socket.close();
  }, timeout);

  socket.onmessage = function(e) {
    clearTimeout(timeout_id);
    onmessage(e);
    socket.close();
  }
}
