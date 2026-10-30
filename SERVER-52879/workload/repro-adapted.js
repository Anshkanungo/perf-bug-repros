// SERVER-52879 workload: Bruce Lucas's repro.js (workload/original/repro.js), minimally adapted.
// Every change from the original is listed in workload/README.md ("Changes from the original").
//
// Run with the legacy 4.4 shell, e.g.:
//   mongo --host <host:port> --quiet --eval 'var CFG={durationSecs:720}' /workload/repro-adapted.js
//
// Output (stdout), one record per line:
//   P,<phase>,<epoch_ms>               phase markers (setup_start, setup_end, insert_start, insert_end)
//   O,<thread>,<start_epoch_ms>,<lat_ms> one line per insert (legacy shell timer resolution = 1 ms)
//   T,<thread>,<inserts>               per-thread totals at the end

var CFG = (typeof CFG === "object" && CFG !== null) ? CFG : {};
var ncollections = CFG.ncollections || 1000;     // original: 1000
var nindexes = CFG.nindexes || 10;               // original: 10
var nthreads = CFG.nthreads || 100;              // original: 100
var durationSecs = CFG.durationSecs || 720;      // original: runs forever
var skipSetup = CFG.skipSetup || false;          // original: always creates indexes
var ptPath = CFG.parallelTester || "/workload/original/parallelTester.js";

load(ptPath);  // original: load("/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js")

function phase(name) {
    print("P," + name + "," + Date.now());
}

function indexes() {
    print("creating indexes");
    phase("setup_start");
    for (var i = 0; i < ncollections; i++) {
        for (var j = 0; j < nindexes; j++) {
            const spec = {};
            spec["f" + j] = 1;
            db["c" + i].createIndex(spec);
        }
    }
    phase("setup_end");
}

function insert() {
    print("inserting");
    var endMs = Date.now() + durationSecs * 1000;
    phase("insert_start");
    var threads = [];
    for (var t = 0; t < nthreads; t++) {
        var thread = new Thread(function(t, ncollections, nindexes, endMs) {
            var buf = [];
            var lastFlush = Date.now();
            for (var i = 0; Date.now() < endMs; i++) {
                var o = {};
                for (var j = 0; j < nindexes; j++)
                    o["f" + j] = i;
                const c = Math.floor(Math.random() * ncollections);
                var t0 = Date.now();
                db["c" + c].insert(o);
                var t1 = Date.now();
                buf.push("O," + t + "," + t0 + "," + (t1 - t0));
                // Flush about once per second, as a single print() call, to keep stdout cheap.
                if (t1 - lastFlush >= 1000) {
                    print(buf.join("\n"));
                    buf = [];
                    lastFlush = t1;
                }
                sleep(100 + Math.random() * 10);
            }
            if (buf.length)
                print(buf.join("\n"));
            return i;
        }, t, ncollections, nindexes, endMs);
        threads.push(thread);
        thread.start();
    }
    for (var t = 0; t < nthreads; t++) {
        threads[t].join();
        print("T," + t + "," + threads[t].returnData());
    }
    phase("insert_end");
}

if (!skipSetup)
    indexes();
insert();
