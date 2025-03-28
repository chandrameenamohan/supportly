import agents

def load_and_process_documents():
    agent = agents.KnowledgeAgent()
    agent.initialize()
    agent.load_and_process_documents()

if __name__ == "__main__":
    load_and_process_documents()