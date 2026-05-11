from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_iv_analysis,
    get_language_instruction,
    get_options_chain,
    get_options_expirations,
    get_put_call_ratio,
    get_short_squeeze_data,
    get_unusual_options_activity,
)


def create_options_squeeze_analyst(llm):
    def options_squeeze_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        ]

        system_message = (
            "You are an options flow and short squeeze analyst. Your task is to"
            " analyze options-derived signals and short interest data for a company"
            " and produce a comprehensive report to inform traders."
            " Follow this workflow:"
            " 1. Check available options expiration dates first using `get_options_expirations`."
            " 2. Analyze put/call ratios for overall sentiment using `get_put_call_ratio`."
            " 3. Scan for unusual options activity (high volume relative to open interest)"
            " using `get_unusual_options_activity`."
            " 4. Assess implied volatility levels and skew using `get_iv_analysis`."
            " 5. Evaluate short squeeze potential using `get_short_squeeze_data`."
            " 6. Optionally inspect a specific options chain using `get_options_chain`"
            " if unusual activity warrants deeper inspection."
            " Synthesize all findings into an actionable report with risk assessment."
            " Include specific numbers, ratios, and thresholds to support your conclusions."
            " Make sure to append a Markdown table at the end of the report to organize"
            " key points in the report, organized and easy to read."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "options_squeeze_report": report,
        }

    return options_squeeze_analyst_node
