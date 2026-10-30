// WT-7264 / SERVER-67350 workload: the `mongo --eval` part of Bruce Lucas's repro.sh
// (workload/original/repro.sh, attached to WT-7264), minimally adapted. Every change from the
// original is listed in workload/README.md ("Changes from the original").
//
// Run with a legacy mongo shell (run.sh uses the one in mongo:5.0.33 for every server version):
//   mongo --host <host:port> --quiet --eval 'var CFG={}' /workload/repro-adapted.js
//
// Output (stdout), one record per line:
//   P,<phase>,<epoch_ms>                         phase markers: setup_start, setup_end, insert_start, insert_end
//   S,<thread>,<batch>,<start_epoch_ms>          an insertMany call starts (so a call still stuck at the run cap is visible)
//   B,<thread>,<batch>,<start_epoch_ms>,<lat_ms> an insertMany call returned (legacy shell timer resolution = 1 ms)
//   T,<thread>,<batches>,<end_epoch_ms>          a thread finished all its batches
//   "<t> <i>" and "thread <t> finished"           the original script's own progress lines, unchanged

var CFG = (typeof CFG === "object" && CFG !== null) ? CFG : {};
var nthreads = CFG.nthreads || 20;          // original: 20
var count = CFG.count || 100 * 1000;         // original: 100*1000 documents per thread
var every = CFG.every || 2000;               // original: 2000 documents per insertMany
var unique = (CFG.unique === undefined) ? true : CFG.unique;  // original: both indexes unique
var syncStart = CFG.syncStart || false;      // original: threads start one after another, no barrier
var skipSetup = CFG.skipSetup || false;      // original: always creates the indexes
var collName = CFG.coll || "c";              // original: db.c
var ptPath = CFG.parallelTester || "/workload/original/parallelTester.js";

load(ptPath);  // original: load("/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js")

function phase(name) {
    print("P," + name + "," + Date.now());
}

if (!skipSetup) {
    phase("setup_start");
    db[collName].createIndex({a: 1}, {unique: unique});
    db[collName].createIndex({b: 1}, {unique: unique});
    phase("setup_end");
}

// Optional (labelled variant, off by default): every thread waits for a common start time before its
// first insertMany, so that all first transactions overlap. The insert phase is then timed from that
// common start time (the threads are created during the ~3 s before it).
var startAt = syncStart ? (Date.now() + 2000 + 50 * nthreads) : 0;

if (syncStart)
    print("P,insert_start," + startAt);
else
    phase("insert_start");
var threads = [];
for (var t = 0; t < nthreads; t++) {
    var thread = new Thread(function(t, count, every, startAt, collName) {
        if (startAt) {
            while (Date.now() < startAt)
                sleep(1);
        }
        var b = 0;
        for (var i = 0; i < count; i += every) {
            var many = [];
            for (var j = 0; j < every; j++) {
                var inx = t * count + i + j;
                many.push({_id: inx, a: inx, b: inx});
            }
            var t0 = Date.now();
            print("S," + t + "," + b + "," + t0);
            db[collName].insertMany(many);
            var t1 = Date.now();
            print("B," + t + "," + b + "," + t0 + "," + (t1 - t0));
            if (i % 10000 == 0)
                print(t, i);
            b++;
        }
        print("thread", t, "finished");
        print("T," + t + "," + b + "," + Date.now());
        return b;
    }, t, count, every, startAt, collName);
    threads.push(thread);
    thread.start();
}
for (var t = 0; t < nthreads; t++)
    threads[t].join();
phase("insert_end");
