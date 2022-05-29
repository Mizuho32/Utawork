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
    <button class="fa-solid fa-backward-step" ontouchend="seek_to(event);"></button>`;
  } else {
    return `
    <button class="fa-solid fa-forward-step"  ontouchend="seek_to(event);"></button>
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

function segment_row(idx, start, end) {
  if (is_mobile_html()) {
    return `
<td class="no">
  <div>
  <label style="text-align: center;" >${idx}</label>
  <input type="checkbox"></input>
  <i class="fa-solid fa-trash" style="text-align: center;" ></i>
  </div>
</td>
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
    <input type="text" class="name" onfocus="on_songname_focus(event);" placeholder="Song name"></input>
  </div>
  <div class="artist"><input type="text" class="artist" placeholder="Artist"></input></div>
</td>`;
  } else {
    return `
<td class="no">${idx}</td>
<td class="time start">${ gen_timeinput(to_time(start)) }</td>
<td class="time end">${   gen_timeinput(to_time(end), false) }</td>
<td class="length">${to_time(end-start, 2)}</td>
<td class="name">
  <button class="fa-solid fa-magnifying-glass" onclick="search_button(event)"></button>
  <input type="text" class="name" onfocus="on_songname_focus(event);"></input>
</td>
<td class="artist"><input type="text" class="artist"></input></td>`;
  }
}

function insert_row(table, idx, start, end) {
  if (idx < 0) idx = table.rows.length;

  let new_row = table.insertRow(-1);
  new_row.setAttribute("class", "item");
  new_row.innerHTML = segment_row(idx, start, end);
  return new_row;
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


