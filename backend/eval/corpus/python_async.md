# Python Asyncio

## The Event Loop

The asyncio event loop is the core of every asyncio application. It schedules
and runs coroutines, handles I/O readiness through the operating system's
selector, and dispatches callbacks. Only one coroutine runs at a time; when a
coroutine awaits an I/O operation it yields control back to the event loop,
which is free to run other ready coroutines in the meantime.

## Coroutines and Tasks

A coroutine is defined with `async def` and must be awaited to run. Wrapping a
coroutine in a Task with `asyncio.create_task` schedules it to run concurrently
on the event loop. Awaiting the task later collects its result. Tasks are how
asyncio achieves concurrency without threads.

## Blocking Calls

Calling a blocking function inside a coroutine stalls the entire event loop,
because nothing else can run until it returns. CPU-bound or blocking work should
be offloaded with `asyncio.to_thread` or a process pool so the loop stays
responsive.
