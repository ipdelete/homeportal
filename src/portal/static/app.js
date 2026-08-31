const SECTIONS = ["tailnet", "network", "services"];

function show(name) {
  if (!SECTIONS.includes(name)) name = "tailnet";
  document.querySelectorAll("nav a").forEach((a) =>
    a.classList.toggle("active", a.hash === "#" + name)
  );
  document.querySelectorAll("main section").forEach((s) =>
    s.classList.toggle("active", s.id === name)
  );
}

window.addEventListener("hashchange", () => show(location.hash.slice(1)));
show(location.hash.slice(1));

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

async function refreshServices() {
  try {
    const res = await fetch("/api/services");
    const data = await res.json();
    const ul = document.getElementById("service-list");
    ul.innerHTML = "";
    for (const s of data.services) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = s.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = s.name;
      li.appendChild(a);
      ul.appendChild(li);
    }
  } catch (e) {
    document.getElementById("service-list").textContent = "Error loading services";
  }
}

refresh();
setInterval(refresh, 30000);
refreshServices();
