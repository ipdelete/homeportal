async function refresh() {
  try {
    const res = await fetch("/api/devices");
    const data = await res.json();
    render(data.devices);
    document.getElementById("updated").textContent =
      "Updated " + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById("updated").textContent = "Error loading devices";
  }
}

function render(devices) {
  const tbody = document.getElementById("devices");
  tbody.innerHTML = "";
  for (const d of devices) {
    const tr = document.createElement("tr");
    tr.className = d.online ? "online" : "offline";

    const name = document.createElement("td");
    name.className = "name";
    name.textContent = d.dns;

    const status = document.createElement("td");
    const dot = document.createElement("span");
    dot.className = "dot";
    status.appendChild(dot);
    status.appendChild(document.createTextNode(d.online ? "online" : "offline"));

    tr.appendChild(name);
    tr.appendChild(status);
    tbody.appendChild(tr);
  }
}

refresh();
setInterval(refresh, 30000);
