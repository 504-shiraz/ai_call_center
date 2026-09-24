import logging

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class AppointmentVoiceAgent(Agent):

    def __init__(self):
        super().__init__(
            instructions=(
                "You are an AI appointment booking assistant. "
                "Be professional and concise."
            )
        )


async def entrypoint(ctx: agents.JobContext):

    logger.info("Connecting to LiveKit room...")

    await ctx.connect()

    logger.info(
        "Connected to room: %s",
        ctx.room.name,
    )

    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=AppointmentVoiceAgent(),
    )


if __name__ == "__main__":

    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
