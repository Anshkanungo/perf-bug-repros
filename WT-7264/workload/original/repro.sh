db=/ssd/db

killall -w -9 mongod mongo mongos
rm -rf $db
mkdir -p $db/r0

mongod --dbpath $db/r0 --logpath $db/r0.log --fork

mongo --quiet --eval '

    load("/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js")


    db.c.createIndex({a: 1}, {unique: true})
    db.c.createIndex({b: 1}, {unique: true})

    nthreads = 20
    threads = []

    for (var t=0; t<nthreads; t++) {
        thread = new Thread(function(t) {
            size = 100
            count = 100*1000;
            every = 2000
            for (var i = 0; i < count; i += every) {
                many = []
                for (j = 0; j < every; j++) {
                    inx = t * count + i + j
                    many.push({_id: inx, a: inx, b: inx})
                }
                db.c.insertMany(many)
                if (i%10000==0) print(t, i)
            }
            print("thread", t, "finished")
        }, t)
        threads.push(thread)
        thread.start()
    }
    for (var t = 0; t < nthreads; t++)
        threads[t].join()
'
