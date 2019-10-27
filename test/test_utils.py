from asyncio import sleep
from unittest import IsolatedAsyncioTestCase, main
from openmaptiles.utils import Action, run_actions


class UtilsTestCase(IsolatedAsyncioTestCase):
    async def test_response(self):
        async def executor(action, dependencies):
            self.assertEqual(dependencies, action.depends_on)
            await sleep(float(action.action_id[1:]) / 200)
            return action.action_id

        async def test(**actions):
            res = await run_actions(
                [Action(k, depends_on=v) for k, v in actions.items()],
                executor
            )
            self.assertEqual(res, list(actions.keys()))

        await test()
        await test(a1=None)
        await test(a1=[], a2=['a1'])
        await test(a1=['a2'], a2=None)
        await test(a1=['a2'], a2=[])
        await test(a1=[], a2=[], a3=['a1', 'a2'])
        await test(a1=[], a2=[], a3=['a1'], a4=['a1', 'a3'], a5=['a2', 'a4'])


if __name__ == '__main__':
    main()
