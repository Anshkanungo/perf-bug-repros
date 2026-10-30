load("/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js")

ncollections = 1000
//ncollections = 100
nindexes = 10

function indexes() {
    print("creating indexes")
    for (var i = 0; i < ncollections; i++) {
        for (var j = 0; j < nindexes; j++) {
            const spec = {}
            spec["f"+j] = 1
            db["c"+i].createIndex(spec)
        }
    }
}


function insert() {

    print("inserting")

    nthreads = 100
    threads = []
    for (var t=0; t<nthreads; t++) {
        thread = new Thread(function(t, ncollections, nindexes) {
            for (var i = 0; ; i++) {
                o = {}
                for (var j = 0; j < nindexes; j++)
                    o["f"+j] = i
                const c = Math.floor(Math.random() * ncollections)
                db["c" + c].insert(o)
                sleep(100 + Math.random() * 10)
            }
        }, t, ncollections, nindexes)
        threads.push(thread)
        thread.start()
    }
    for (var t = 0; t < nthreads; t++)
        threads[t].join()
}

indexes()
insert()

