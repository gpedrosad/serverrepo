#!/usr/bin/env node
/**
 * Add / refresh Private Trainer Dummy item (20155) in items-zagan-test.otb.
 *
 * Placement item must use a CLIENT id that is Use-able in Tibia.dat.
 * Starbinder hood (20118 / clientId 4835) is a helmet → client equips on Use
 * and never runs the action. We reuse wooden chair kit clientId (3901 → 2775).
 *
 * Creature look stays on server id 20118 (hood sprite) via monster XML.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const OTB = path.join(ROOT, "server/YurOTS/ots/data/items/items-zagan-test.otb");

const NEW_SERVER_ID = 20155;
// Construction kit: usable in client DAT (Use works). Not a helmet.
const CLIENT_ID_PROTOTYPE_SERVER_ID = 3901; // wooden chair kit → clientId 2775
const NAME = "private trainer dummy";
const DESCR = "Put it on a free house tile and use it to place a training dummy.";

const NODE_START = 0xfe;
const NODE_END = 0xff;
const ESCAPE = 0xfd;

const GROUP_NONE = 0;
const FLAG_USEABLE = 16;
const FLAG_PICKUPABLE = 32;
const FLAG_MOVEABLE = 64;
const FLAGS = FLAG_USEABLE | FLAG_PICKUPABLE | FLAG_MOVEABLE; // 0x70

function escapeProps(buf) {
  const out = [];
  for (const b of buf) {
    if (b === NODE_START || b === NODE_END || b === ESCAPE) out.push(ESCAPE);
    out.push(b);
  }
  return Buffer.from(out);
}

function findServerIdAttr(data, serverId) {
  const needle = Buffer.from([0x10, 0x02, 0x00, serverId & 0xff, (serverId >> 8) & 0xff]);
  return data.indexOf(needle);
}

function findNodeBounds(data, attrIdx) {
  let start = -1;
  for (let i = attrIdx; i >= 0; i--) {
    if (data[i] === NODE_START && (i === 0 || data[i - 1] !== ESCAPE)) {
      start = i;
      break;
    }
  }
  if (start < 0) throw new Error("NODE_START not found");

  let i = start + 1;
  let end = -1;
  while (i < data.length) {
    if (data[i] === ESCAPE) {
      i += 2;
      continue;
    }
    if (data[i] === NODE_START) {
      end = i;
      break;
    }
    if (data[i] === NODE_END) {
      end = i + 1;
      break;
    }
    i++;
  }
  if (end < 0) throw new Error("node end not found");
  return { start, end };
}

function clientIdOf(data, serverId) {
  const idx = findServerIdAttr(data, serverId);
  if (idx < 0) throw new Error(`server id ${serverId} not in OTB`);
  const j = data.indexOf(Buffer.from([0x11, 0x02, 0x00]), idx, idx + 24);
  if (j < 0) throw new Error(`client id missing for ${serverId}`);
  return data.readUInt16LE(j + 3);
}

function attr(id, payload) {
  const len = Buffer.alloc(2);
  len.writeUInt16LE(payload.length, 0);
  return Buffer.concat([Buffer.from([id]), len, payload]);
}

function u16(n) {
  const b = Buffer.alloc(2);
  b.writeUInt16LE(n, 0);
  return b;
}

function buildNode(serverId, clientId) {
  const flags = Buffer.alloc(4);
  flags.writeUInt32LE(FLAGS, 0);
  const props = Buffer.concat([
    flags,
    attr(0x10, u16(serverId)),
    attr(0x11, u16(clientId)),
    attr(0x12, Buffer.from(NAME, "ascii")),
    attr(0x13, Buffer.from(DESCR, "ascii")),
  ]);
  return Buffer.concat([
    Buffer.from([NODE_START, GROUP_NONE]),
    escapeProps(props),
    Buffer.from([NODE_END]),
  ]);
}

function main() {
  if (!fs.existsSync(OTB)) {
    console.error("ERROR: missing", OTB);
    process.exit(1);
  }

  let data = Buffer.from(fs.readFileSync(OTB));
  const clientId = clientIdOf(data, CLIENT_ID_PROTOTYPE_SERVER_ID);
  const newNode = buildNode(NEW_SERVER_ID, clientId);

  const existing = findServerIdAttr(data, NEW_SERVER_ID);
  if (existing >= 0) {
    const { start, end } = findNodeBounds(data, existing);
    data = Buffer.concat([data.slice(0, start), newNode, data.slice(end)]);
    console.log(
      `OK replaced id=${NEW_SERVER_ID} in ${path.basename(OTB)} ` +
        `(clientId=${clientId} from kit ${CLIENT_ID_PROTOTYPE_SERVER_ID})`
    );
  } else {
    let insertAt = data.length;
    if (data[data.length - 1] === NODE_END) insertAt = data.length - 1;
    data = Buffer.concat([data.slice(0, insertAt), newNode, data.slice(insertAt)]);
    console.log(
      `OK added id=${NEW_SERVER_ID} to ${path.basename(OTB)} ` +
        `(clientId=${clientId} from kit ${CLIENT_ID_PROTOTYPE_SERVER_ID})`
    );
  }

  fs.writeFileSync(OTB, data);

  const verify = fs.readFileSync(OTB);
  if (findServerIdAttr(verify, NEW_SERVER_ID) < 0) {
    console.error("ERROR: verify failed — new id not found after write");
    process.exit(1);
  }
  if (clientIdOf(verify, NEW_SERVER_ID) !== clientId) {
    console.error("ERROR: verify failed — clientId mismatch");
    process.exit(1);
  }
  console.log(`OK name="${NAME}" flags=0x${FLAGS.toString(16)} usable+pickupable+moveable`);
  console.log("NOTE: monster look should stay on server id 20118 (hood sprite).");
}

main();
