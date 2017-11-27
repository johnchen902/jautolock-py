# python-jautolock

## Description

This is a rewrite of original jautolock in Python.

jautolock will fire a program after specified time of user inactivity.
It has basically the same functionality as xautolock,
but is designed to be more flexible.
You can specify any number of tasks, instead of only three.
Smallest time unit is second for now.

## Usage

Unlike xautolock, jautolock has no default locker.
You must tell jautolock what program to fire, like this:

```bash
jautolock start -t notify,50s,'notify-send jautolock "10 seconds before locking"' \
                -t lock,60s,'i3lock -n' \
                -t screenoff,70s,'xset dpms force off'
```

Supported time units are h (hours), m (minutes) and s (seconds).

Like xautolock, jautolock can communicate with an already running instance.
For now, you must manually connect to `$XDG_RUNTIME_DIR/jautolock.socket`.
Currently these messages are understood:

+ `now <taskname>`: Fire all tasks with the specified name.
+ `busy`: Assume the user is always active.
+ `unbusy`: Don't keep assuming the user is always active.

## Timing

*Need help writing this section.*
