// Copyright (C) 2023 Prosys Lab, KAIST (https://prosys.kaist.ac.kr)
//
// This program is modified from the original version by the following authors:
// Art, Science, and Engineering of Fuzzing
// Copyright (C) 2019 Sang Kil Cha
//
// This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.md.
// This is free software, and you are welcome to redistribute it under certain
// conditions; see COPYING.md for details.

"use strict";

// The minimum scale that we can set.
const minScale = 0.2;

// The currently selected node's name.
var currentSelection = undefined;

function createCanvas() {
  return d3.select("#js-canvas")
    .append("svg")
    .attr("width", "100%")
    .attr("height", "100%")
}

function parseJSONData(arr, replay) {
  let dict = {};
  var data = {
    "nodes": [],
    "links": []
  };
  $.each(arr["nodes"], function (_, obj) {
    var node = {
      "name": obj,
      "children": [],
      "parents": [],
      "found_time": replay[obj]["found_time"],
      "time_delta": replay[obj]["time_delta"],
      "mutation": replay[obj]["mutation"],
      "mutation_delta": replay[obj]["mutation_delta"],
      "coverage": replay[obj]["coverage"]
    };
    dict[obj] = node;
    data.nodes.push(node);
  });
  let edges = arr["edges"];
  $.each(edges, function (_, obj) {
    dict[obj[0]].children.push(obj[1]);
    dict[obj[1]].parents.push(obj[0]);
    data.links.push({
      "source": obj[0],
      "target": obj[1]
    });
  });
  return data;
}

function drawEdges(g, d) {
  g.append("defs")
    .selectAll("marker")
    .data(["arrow"])
    .enter().append("marker")
    .attr("id", d => d)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 15)
    .attr("refY", -1.5)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("fill", "#999")
    .attr("d", "M0,-5L10,0L0,5");

  return g.append("g")
    .attr("stroke", "#999")
    .attr("stroke-opacity", 0.6)
    .selectAll()
    .data(d.links)
    .join("line")
    .attr("stroke-width", _ => 2)
    .attr("marker-end", _ => `url(${new URL(`#arrow`, location)})`);
}

function buildAuthors(node) {
  let s = "";
  $.each(node.author, function (i, a) {
    if (i == node.author.length - 1 && node.author.length > 1)
      s += ", and " + a;
    else s += ", " + a;
  });
  return s;
}

function buildRef(node) {
  let s = "";
  if (node.title !== undefined) {
    s += "\"" + node.title + "\"";
  } else {
    s += "\"" + node.name + "\"";
  }
  if (node.author !== undefined) {
    s += buildAuthors(node);
  }
  if (node.booktitle !== undefined) {
    s += ". In " + node.booktitle;
  }
  if (node.journal !== undefined) {
    s += ". " + node.journal + ", " + node.volume + "(" + node.number + ")";
  }
  if (node.year !== undefined) {
    s += ", " + node.year;
  }
  return s;
}

function constructIcon(faName, title) {
  return "<i class=\"fa " + faName + "\" title = \"" + title + "\"></i> ";
}

function constructCharSpan(ch, title) {
  return "<i title = \"" + title + "\">" + ch + "</i> ";
}

function appendToolURL(list, node) {
  const item = list.append("li").classed("list-group-item", true);
  item.append("b").text("Tool URL: ");
  if (node.toolurl !== undefined)
    item.append("a")
      .classed("infobox__icon", true)
      .attr("href", node.toolurl)
      .html(constructIcon("fa-wrench", "Tool available"));
  else
    item.append("span").text("Not available.");
}

function appendPredecessors(list, node, nodes, zoom, canvas, width, height) {
  const pred = list.append("li").classed("list-group-item", true);
  pred.append("b").text("Parents: ");
  if (node.parents !== undefined)
    $.each(node.parents, function (_, name) {
      const matches = nodes.filter(function (n) {
        return n.name === name;
      });
      matches.each(function (d, _) {
        pred.append("button")
          .attr("class", "btn btn-outline-primary")
          .text(name + "  ")
          .on("click", _ =>
            onClick(d, nodes, zoom, canvas, width, height)
          );
      });
    });
  else
    pred.append("span").text("");
}

function appendSuccessors(list, node, nodes, zoom, canvas, width, height) {
  const succ = list.append("li").classed("list-group-item", true);
  succ.append("b").text("Children: ");
  if (node.children !== undefined)
    $.each(node.children, function (_, name) {
      const matches = nodes.filter(function (n) {
        return n.name === name;
      });
      matches.each(function (d, _) {
        succ.append("button")
          .attr("class", "btn btn-outline-primary")
          .text(name + "  ")
          .on("click", _ =>
            onClick(d, nodes, zoom, canvas, width, height)
          );
      });
    });
  else
    succ.append("span").text("");
}

function appendInfos(list, node) {
  const succ = list.append("li").classed("list-group-item", true);
  const infoContainer = succ.append("div");  // Use a block-level element for line breaks
  infoContainer.append("b").text("Coverage info: ");
  const ul1 = infoContainer.append("ul");  // Create an unordered list
  ul1.append("li").text(String(node.coverage));

  infoContainer.append("b").text("Found time: ");
  const ul2 = infoContainer.append("ul");  // Create an unordered list
  ul2.append("li").text("At " + String(node.found_time) + " seconds");

  infoContainer.append("b").text("Time since parent: ");
  const ul3 = infoContainer.append("ul");  // Create an unordered list
  ul3.append("li").text("After " + String(node.time_delta) + " seconds");

  infoContainer.append("b").text("Mutation: ");
  const ul4 = infoContainer.append("ul");  // Create an unordered list
  ul4.append("li").text(String(node.mutation));

  // infoContainer.append("b").text("Mutation delta: ");
  // const ul4 = infoContainer.append("ul");  // Create an unordered list
  // ul4.append("li").text(String(node.mutation_delta));

  infoContainer.append("b").text("Mutation delta: ");
  const ul5 = infoContainer.append("ul");  // Create an unordered list
  const fileLink = "mutation_delta/" + node.name + ".txt"; // Replace this with the actual path to the file
  ul5.append("li").append("a")
    .attr("href", fileLink)
    .attr("target", "_blank") // Open link in a new tab
    .text("View File");
}

function setTitle(node) {
  if (node === undefined) {
    d3.select("#js-infobox-title").text("Select a seed");
  } else {
    d3.select("#js-infobox-title")
      .text(node.name);
  }
}

function clearContents() {
  return d3.select("#js-infobox-content").html("");
}

function showInfobox() {
  d3.select("#js-infobox").style("display", "block");
}

function hideInfobox() {
  d3.select("#js-infobox").style("display", "none");
}

function colorPredecessors(node, nodes) {
  nodes.select(".node").attr("fill", function (d) {
    if (node.parents.includes(d.name)) {
      colorPredecessors(d, nodes);
      return "red";
    }
    else if (d.name.includes("Crash")) {
      return "lightgreen";
    }
    else {
      return "white";
    }
  }
  );
}


function clickNode(node, nodes, zoom, canvas, width, height) {
  let list = clearContents().append("ul").classed("list-group", true);
  appendPredecessors(list, node, nodes, zoom, canvas, width, height);
  appendSuccessors(list, node, nodes, zoom, canvas, width, height);
  appendInfos(list, node);
  setTitle(node);
  currentSelection = node.name;
  showInfobox();
  colorPredecessors(node, nodes);

}

function onClick(node, nodes, zoom, canvas, width, height) {
  const resultList = d3.select("#js-searchform-result");
  const k = 2.0;
  const x = -node.x * k + width / 2;
  const y = -node.y * k + height / 2;
  clickNode(node, nodes, zoom, canvas, width, height);
  clearSearchResults(nodes, resultList);
  canvas.transition().duration(750)
    .call(zoom.transform,
      d3.zoomIdentity.translate(x, y).scale(k));
}

function drawNodes(g, d, simulation, zoom, canvas, width, height, replay) {
  const nodes = g.append("g")
    .selectAll("g")
    .data(d.nodes)
    .enter()
    .append("g")

  function dragStart(d) {
    if (!d.active) simulation.alphaTarget(0.3).restart();
    d.subject.fx = d.subject.x;
    d.subject.fy = d.subject.y;
    d.isDragging = true;
  }

  function dragMiddle(d) {
    d.subject.fx = d.x;
    d.subject.fy = d.y;
  }

  function dragEnd(d) {
    if (!d.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
    d.isDragging = false;
  }

  nodes.append("ellipse")
    .attr("rx", 70)
    .attr("ry", 12)
    .attr("id", d => d.name)
    .attr("fill", d => {
      if (d.name.includes("Crash")) {
        return "lightgreen";
      } else {
        return "white";
      }
    })
    .attr("stroke", "grey")
    .attr("stroke-width", 1.5)
    .attr("class", "node")
    .on("click", (_, d) => onClick(d, nodes, zoom, canvas, width, height))
    .call(d3.drag()
      .on("start", dragStart)
      .on("drag", dragMiddle)
      .on("end", dragEnd));

  nodes.append('text')
    .attr("class", "nodetext")
    .attr("dominant-baseline", "central")
    .attr('text-anchor', "middle")
    .attr("font-size", "10px")
    .text(function (d) {
      return d.name
    })
    .on("click", (_, d) => onClick(d, nodes, zoom, canvas, width, height))

  const dragHandler = d3.drag()
    .on("start", dragStart)
    .on("drag", dragMiddle)
    .on("end", dragEnd);
  dragHandler(nodes);

  return nodes;
}

function drawReplay(replay) {
  const counts = []
  for (var key in replay["visit"]) {
    counts.push(replay["visit"][key])
  }

  // see https://d3js.org/d3-scale-chromatic/sequential
  const colorScale = d3.scaleSequential(d3.interpolateReds)
    .domain([d3.min(counts), d3.max(counts)]);

  // visited node
  for (var key in replay["visit"]) {
    d3.select("#" + key).attr("fill", _ => {
      return colorScale(replay["visit"][key])
    })
  }

  // draw target node larger
  d3.select("#" + replay["target"])
    .attr("rx", 140)
    .attr("ry", 24)
}

function installZoomHandler(canvas, g) {
  function zoomed(event) {
    g.attr('transform', event.transform);
  }
  const zoomHandler = d3.zoom().on('zoom', zoomed);
  canvas.call(zoomHandler);
  return zoomHandler;
}

function escapeRegExp(string) {
  return string.replace(/[.*+\-?^${}()|[\]\\]/g, '\\$&').replace(/[,]/g, "|");
}

function hideSearchBar(resultList) {
  resultList.html("");
}

function clearSearchResults(nodes, resultList) {
  nodes.select(".node").classed("node-found", function (node) {
    return (currentSelection === node.name);
  });
  hideSearchBar(resultList);
}

function installSearchHandler(width, height, canvas, zoom, nodes) {
  const txt = $("#js-searchform-text");
  const resultList = d3.select("#js-searchform-result");
  let items = null;
  let itemidx = -1;

  function performSearch(s) {
    const escaped = escapeRegExp(s);
    const re = new RegExp(escaped, "i");
    itemidx = -1;
    clearSearchResults(nodes, resultList);
    if (escaped === "") return;
    const matches = nodes.filter(function (n) {
      return n.name.match(re) !== null;
    });
    matches.select(".node").classed("node-found", true);
    const maxShow = 10;
    matches.each(function (d, i) {
      if (i >= maxShow) return;
      resultList.append("li")
        .classed("list-group-item", true)
        .classed("py-1", true)
        .text(d.name)
        .on("click", function () {
          onClick(d, nodes, zoom, canvas, width, height);
        });
    });
  };

  function getCurrentResult() {
    return resultList.selectAll(".list-group-item")
      .classed("active", false).nodes();
  };
  txt.click(function (_) {
    clearSearchResults(nodes, resultList);
  });
  txt.keydown(function (e) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") return false;
    else return true;
  });
  txt.keyup(function (e) {
    if (e.shiftKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Enter" || e.keyCode === 13) {
      if (itemidx >= 0 && itemidx <= items.length - 1) {
        $(items[itemidx]).trigger("click");
        itemidx = -1;
      } else {
        hideSearchBar(resultList);
      }
    } else if (e.key === "ArrowUp" || e.keyCode === 38) {
      items = getCurrentResult();
      itemidx = Math.max(itemidx - 1, 0);
      d3.select(items[itemidx]).classed("active", true);
      return false;
    } else if (e.key === "ArrowDown" || e.keyCode === 40) {
      items = getCurrentResult();
      itemidx = Math.min(itemidx + 1, items.length - 1);
      d3.select(items[itemidx]).classed("active", true);
      return false;
    } else {
      performSearch(txt.val());
    }
  });
}

function installClickHandler() {
  const resultList = d3.select("#js-searchform-result");
  $(document).on("click", "svg", function (_) {
    hideSearchBar(resultList);
  });
}

function installDragHandler() {
  const infobox = d3.select("#js-infobox");
  $("#js-infobox").resizable({
    handles: {
      w: $("#js-separator")
    },
    resize: function (_e, ui) {
      const orig = ui.originalSize.width;
      const now = ui.size.width;
      const width = orig + orig - now;
      infobox.style("flex-basis", width + "px");
      infobox.style("width", null);
      infobox.style("height", null);
    }
  });
}

function installInfoBoxCloseHandler() {
  $("#js-infobox-close").click(function () {
    hideInfobox();
  });
}

function computeYPos(year) {
  return (year - theFirstYear) * yearHeight;
}

function initSimulation(d, simulation, width, height, links, nodes) {
  function ticked() {
    links
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);
    nodes.attr('transform', d => `translate(${d.x},${d.y})`);
  }

  simulation.nodes(d.nodes)
    .force("link", d3.forceLink(d.links).id(d => d.name))
    .force("charge", d3.forceManyBody().strength(-500).distanceMax(800))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collison", d3.forceCollide().radius(50))
    .on("tick", ticked);
}

function addStatItem(dict, key, id) {
  if (key in dict) dict[key].push(id);
  else dict[key] = [id];
}

function sortByCount(stats) {
  const items = Object.keys(stats).map(function (k) {
    return [k, stats[k]];
  });
  items.sort(function (fst, snd) {
    const sndLen = snd[1].length;
    const fstLen = fst[1].length;
    if (sndLen == fstLen) {
      return fst[0].localeCompare(snd[0]); // lexicographical sorting
    } else {
      return sndLen - fstLen;
    }
  });
  return items;
}

function sortFuzzersByYear(fuzzerMap, fuzzers) {
  fuzzers.sort(function (fst, snd) {
    return fuzzerMap[snd].year - fuzzerMap[fst].year;
  });
  return fuzzers;
}

function makeAccordionElm(handle, myid, header, fuzzers, fnLink) {
  const card = d3.select(handle)
    .append("div").classed("card", true);
  card
    .append("div").classed("card-header", true).attr("role", "tab")
    .append("h6").classed("mb-0", true).classed("small", true)
    .append("div")
    .attr("role", "button")
    .attr("data-toggle", "collapse")
    .attr("data-target", "#" + myid)
    .html(header);
  card
    .append("div").classed("collapse", true).attr("id", myid)
    .append("div").classed("card-body", true)
    .append("h6").classed("small", true)
    .append("ul").classed("list-group", true)
    .selectAll("li")
    .data(fuzzers)
    .enter()
    .append("li").html(function (f) {
      return fnLink(f);
    });
  return $(card.node()).detach();
}

function fuzzerToString(fuzzer) {
  let s = fuzzer.name;
  if (fuzzer.year !== undefined) s += " " + fuzzer.year;
  if (fuzzer.author !== undefined) s += " " + fuzzer.author.join();
  if (fuzzer.title !== undefined) s += " " + fuzzer.title;
  if (fuzzer.booktitle !== undefined) s += " " + fuzzer.booktitle;
  if (fuzzer.targets !== undefined) s += " " + fuzzer.targets.join();
  return s;
}

function makeAnchor(fuzzerMap, f) {
  const fuzzer = fuzzerMap[f];
  return "<a href=\"./?k=" + f + "\">" + buildRef(fuzzer) + "</a>" +
    "<span style=\"display: none\">" +
    fuzzerToString(fuzzerMap[f]) + "</span>";
}

function makeAccordion(fuzzerMap, data, id, handle) {
  const stats = [];
  const sorted = sortByCount(data);
  sorted.forEach(function (data) {
    const name = data[0];
    const fuzzers = data[1];
    const myid = "js-" + id + "-" + name.replace(/\s/g, "");
    const header = name + " (<span>" + fuzzers.length + "</span>)";
    const fnLink = function (f) {
      return makeAnchor(fuzzerMap, f);
    };
    stats.push(
      makeAccordionElm(handle, myid, header,
        sortFuzzersByYear(fuzzerMap, fuzzers), fnLink));
  });
  return stats;
}

function makeVenueAccordion(fuzzerMap, venues) {
  return makeAccordion(fuzzerMap, venues, "venue", "#js-stats-body__venues");
}

function makeTargetAccordion(fuzzerMap, targets) {
  return makeAccordion(fuzzerMap, targets, "target", "#js-stats-body__targets");
}

function makeAuthorAccordion(fuzzerMap, authors) {
  return makeAccordion(fuzzerMap, authors, "author", "#js-stats-body__authors");
}

function filterAndSortAccordion(acc, str, container) {
  const elms = [];
  acc.forEach(function (elm) {
    let matches = 0;
    elm.find("ul > li").each(function () {
      const listElm = $(this);
      const m = listElm.find("span:contains('" + str + "')");
      if (m.length) {
        matches += 1;
        $(this).show();
      }
    });
    if (matches > 0) {
      elms.push([matches, elm]);
      elm.find("div > span").text(matches);
    }
  });
  elms.sort(function (fst, snd) {
    return snd[0] - fst[0];
  });
  elms.forEach(function (elm) {
    container.append(elm[1]);
  });
}

function registerStatsFilter(venueAcc, targetAcc, authorAcc) {
  $("#js-stats-body__filter").on("change keyup paste click", function () {
    const t = $(this).val();
    $(".card li").each(function () {
      $(this).hide();
    });
    $("#js-stats-body__venues").empty();
    $("#js-stats-body__targets").empty();
    $("#js-stats-body__authors").empty();
    filterAndSortAccordion(venueAcc, t, $("#js-stats-body__venues"));
    filterAndSortAccordion(targetAcc, t, $("#js-stats-body__targets"));
    filterAndSortAccordion(authorAcc, t, $("#js-stats-body__authors"));
  });
}

function initStats(data) {
  const fuzzerMap = {};
  const venues = {};
  const targets = {};
  const authors = {};
  data.forEach(function (v) {
    fuzzerMap[v.name] = v;
    if (v.author !== undefined)
      v.author.forEach(function (a) {
        addStatItem(authors, a, v.name);
      });
    if (v.booktitle !== undefined)
      addStatItem(venues, v.booktitle, v.name);
    v.targets.forEach(function (t) {
      addStatItem(targets, t, v.name);
    });
  });
  d3.select("#js-stats-body__summary").append("p")
    .text("Currently, there are a total of " +
      data.length +
      " fuzzers and " +
      Object.keys(authors).length +
      " authors in the DB, collected from " +
      Object.keys(venues).length +
      " different venues.");
  const venueAcc = makeVenueAccordion(fuzzerMap, venues);
  const targetAcc = makeTargetAccordion(fuzzerMap, targets);
  const authorAcc = makeAuthorAccordion(fuzzerMap, authors);
  $.expr[':'].contains = function (n, _, m) {
    return jQuery(n).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
  };
  filterAndSortAccordion(venueAcc, "", $("#js-stats-body__venues"));
  filterAndSortAccordion(targetAcc, "", $("#js-stats-body__targets"));
  filterAndSortAccordion(authorAcc, "", $("#js-stats-body__authors"));
  registerStatsFilter(venueAcc, targetAcc, authorAcc);
}

function getQueryVariable(variable) {
  var query = window.location.search.substring(1);
  var vars = query.split('&');
  for (var i = 0; i < vars.length; i++) {
    var pair = vars[i].split('=');
    if (decodeURIComponent(pair[0]) == variable) {
      return decodeURIComponent(pair[1]);
    }
  }
  return undefined;
}

Promise.all([
  d3.json("seed_graph.json"),
  d3.json("metadata.json")
]).then(function ([json, replay]) {
  const width = $("#js-canvas").width();
  const height = $("#js-canvas").height();
  const canvas = createCanvas();
  const simulation = d3.forceSimulation();
  const g = canvas.append("g");
  const d = parseJSONData(json, replay);
  const links = drawEdges(g, d);
  const zoom = installZoomHandler(canvas, g);
  const nodes = drawNodes(g, d, simulation, zoom, canvas, width, height, replay);
  installSearchHandler(width, height, canvas, zoom, nodes);
  installClickHandler();
  installDragHandler();
  installInfoBoxCloseHandler();
  initSimulation(d, simulation, width, height, links, nodes);
  initStats(d.nodes);
  zoom.scaleTo(canvas, minScale);
  // Center the graph after a sec.
  setTimeout(function () {
    const key = getQueryVariable("k");
    const data = d.nodes.find(function (d) {
      return (d.id === key);
    });
    if (key === undefined || data === undefined) {
      const graphScale = d3.zoomTransform(g.node()).k;
      const y = height / 2 / graphScale;
      zoom.translateTo(canvas, 0, y);
    } else {
      setTimeout(function () {
        onClick(data, nodes, zoom, canvas, width, height);
      }, 1000);
    }
  }, 500);
})
