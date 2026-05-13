# Context
We're doing a workshop to practice our agentic coding skills. We got a practice project that we're working with, defined in project.md. We have about 3 hours time to set up the project. 

# Basics for the agent
The coding agent should stick to these basics at all times:
## Clean coding
Write code that is considered 'high quality' part of this is:
- Add tests for core logic
- Keep code duplication to a miniumum
- Delete unused code
- Write frequent commit messages description the content
- Do not commit security sensitive content like API keys
- Strongly type every variable
- Give variables sensible names
- Set up a good linter/typechecker environment
- Add a linter and fix linting errors
- Add and update readmes that outline how to use the project and include demo instructions
- Keep modules/files small (<~1000LOC), separate code into sensible files
- Keep functions small, give each function a sensible name(~<200LOC)
- Add documentation to every function that is not simple a repetition of the function name, explain inputs and outputs

## Project definition, project.md
Project.md contains the definition of the project, could also be called a PRD. It includes requirements and so on. The project spec is very minimal at first but should grow as we work. Make sure to update it when new features are added.  

## Architecture document, design.md
Maintain an design document that outlines the overall design and the structure of the project. Make sure all mayor decisions are recoded in the document.

## Feedback
If some important decisions have not been made, ask me about them and keep track of the decision in the project and design document. 

