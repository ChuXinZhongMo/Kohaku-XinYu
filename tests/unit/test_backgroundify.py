"""Tests for the backgroundify wrapper — mid-flight task promotion."""

import asyncio

import pytest

from kohakuterrarium.core.backgroundify import (
    BackgroundifyHandle,
    PromotionResult,
    backgroundify,
)


class TestBackgroundifyHandle:
    """Core handle behavior."""

    @pytest.mark.asyncio
    async def test_fast_task_returns_real_result(self):
        """Task that completes before any promotion returns its result."""

        async def fast():
            return "done"

        task = asyncio.create_task(fast())
        handle = BackgroundifyHandle(task, "job_1")
        result = await handle.wait()

        assert result == "done"
        assert not handle.promoted
        assert handle.done

    @pytest.mark.asyncio
    async def test_slow_task_promoted(self):
        """Promoting a slow task returns PromotionResult."""

        async def slow():
            await asyncio.sleep(10)
            return "done"

        task = asyncio.create_task(slow())
        handle = BackgroundifyHandle(task, "job_1")

        await asyncio.sleep(0.01)
        assert handle.promote() is True

        result = await handle.wait()
        assert isinstance(result, PromotionResult)
        assert result.job_id == "job_1"
        assert handle.promoted

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_promote_after_completion_returns_false(self):
        """Cannot promote a task that already finished."""

        async def fast():
            return "done"

        task = asyncio.create_task(fast())
        handle = BackgroundifyHandle(task, "job_1")
        await handle.wait()

        assert handle.promote() is False
        assert not handle.promoted

    @pytest.mark.asyncio
    async def test_cancel_propagates(self):
        """Cancelling the underlying task propagates through wait()."""

        async def slow():
            await asyncio.sleep(10)
            return "done"

        task = asyncio.create_task(slow())
        handle = BackgroundifyHandle(task, "job_1")

        # Cancel from outside
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await handle.wait()

    @pytest.mark.asyncio
    async def test_callback_fires_on_promoted_completion(self):
        """on_bg_complete fires when a promoted task finishes."""
        callback_results = []

        async def on_complete(job_id, result):
            callback_results.append((job_id, result))

        async def medium():
            await asyncio.sleep(0.05)
            return "result_data"

        task = asyncio.create_task(medium())
        handle = BackgroundifyHandle(task, "job_1", on_bg_complete=on_complete)
        handle.promote()

        result = await handle.wait()
        assert isinstance(result, PromotionResult)

        # Wait for the actual task to finish and callback to fire
        await asyncio.sleep(0.15)
        assert len(callback_results) == 1
        assert callback_results[0] == ("job_1", "result_data")

    @pytest.mark.asyncio
    async def test_callback_not_fired_for_direct_completion(self):
        """on_bg_complete does NOT fire when task completes as direct."""
        callback_results = []

        async def on_complete(job_id, result):
            callback_results.append((job_id, result))

        async def fast():
            return "done"

        task = asyncio.create_task(fast())
        handle = BackgroundifyHandle(task, "job_1", on_bg_complete=on_complete)
        result = await handle.wait()

        assert result == "done"
        await asyncio.sleep(0.05)
        assert len(callback_results) == 0  # Not promoted, no callback

    @pytest.mark.asyncio
    async def test_callback_receives_exception(self):
        """on_bg_complete receives the exception when promoted task fails."""
        callback_results = []

        async def on_complete(job_id, result):
            callback_results.append((job_id, result))

        async def failing():
            await asyncio.sleep(0.05)
            raise ValueError("boom")

        task = asyncio.create_task(failing())
        handle = BackgroundifyHandle(task, "job_1", on_bg_complete=on_complete)
        handle.promote()
        await handle.wait()

        await asyncio.sleep(0.15)
        assert len(callback_results) == 1
        assert isinstance(callback_results[0][1], ValueError)

    @pytest.mark.asyncio
    async def test_properties(self):
        """Property accessors work correctly."""

        async def slow():
            await asyncio.sleep(10)

        task = asyncio.create_task(slow())
        handle = BackgroundifyHandle(task, "test_id")

        assert handle.job_id == "test_id"
        assert handle.promoted is False
        assert handle.done is False
        assert handle.task is task

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestBackgroundifyFactory:
    """Tests for the backgroundify() factory function."""

    @pytest.mark.asyncio
    async def test_background_init_true(self):
        """background_init=True promotes immediately."""

        async def slow():
            await asyncio.sleep(10)
            return "done"

        task = asyncio.create_task(slow())
        handle = backgroundify(task, "job_1", background_init=True)

        assert handle.promoted is True

        result = await handle.wait()
        assert isinstance(result, PromotionResult)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_background_init_false(self):
        """background_init=False (default) does not promote."""

        async def fast():
            return "done"

        task = asyncio.create_task(fast())
        handle = backgroundify(task, "job_1", background_init=False)

        assert handle.promoted is False
        result = await handle.wait()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_factory_with_callback(self):
        """Factory wires the callback correctly."""
        callback_results = []

        async def on_complete(job_id, result):
            callback_results.append((job_id, result))

        async def medium():
            await asyncio.sleep(0.05)
            return "data"

        task = asyncio.create_task(medium())
        handle = backgroundify(
            task, "job_1", on_bg_complete=on_complete, background_init=True
        )
        await handle.wait()

        await asyncio.sleep(0.15)
        assert callback_results == [("job_1", "data")]


class TestConcurrentHandles:
    """Tests simulating multiple handles being waited on."""

    @pytest.mark.asyncio
    async def test_multiple_handles_one_promoted(self):
        """Simulate wait loop: 3 tasks, 1 promoted mid-wait."""

        async def fast():
            await asyncio.sleep(0.02)
            return "fast_result"

        async def slow():
            await asyncio.sleep(10)
            return "slow_result"

        t1 = asyncio.create_task(fast())
        t2 = asyncio.create_task(slow())
        t3 = asyncio.create_task(fast())

        h1 = backgroundify(t1, "j1")
        h2 = backgroundify(t2, "j2")
        h3 = backgroundify(t3, "j3")

        # Promote h2 after a brief delay
        async def promote_later():
            await asyncio.sleep(0.01)
            h2.promote()

        asyncio.create_task(promote_later())

        # Simulate the wait loop
        pending = {"j1": h1, "j2": h2, "j3": h3}
        results = {}
        promoted = []

        while pending:
            futures = {
                asyncio.ensure_future(h.wait()): jid for jid, h in pending.items()
            }
            done, _ = await asyncio.wait(
                futures.keys(), return_when=asyncio.FIRST_COMPLETED
            )
            for f in done:
                jid = futures[f]
                pending.pop(jid)
                r = f.result()
                if isinstance(r, PromotionResult):
                    promoted.append(jid)
                else:
                    results[jid] = r
            for f in futures:
                if f not in done:
                    f.cancel()

        assert "j1" in results and results["j1"] == "fast_result"
        assert "j3" in results and results["j3"] == "fast_result"
        assert "j2" in promoted

        t2.cancel()
        try:
            await t2
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_all_complete_no_promotion(self):
        """All tasks complete normally — no promotions."""

        async def fast(val):
            await asyncio.sleep(0.01)
            return val

        handles = {
            f"j{i}": backgroundify(asyncio.create_task(fast(f"r{i}")), f"j{i}")
            for i in range(5)
        }
        results = {}
        pending = dict(handles)

        while pending:
            futures = {
                asyncio.ensure_future(h.wait()): jid for jid, h in pending.items()
            }
            done, _ = await asyncio.wait(
                futures.keys(), return_when=asyncio.FIRST_COMPLETED
            )
            for f in done:
                jid = futures[f]
                pending.pop(jid)
                results[jid] = f.result()
            for f in futures:
                if f not in done:
                    f.cancel()

        assert len(results) == 5
        for i in range(5):
            assert results[f"j{i}"] == f"r{i}"
