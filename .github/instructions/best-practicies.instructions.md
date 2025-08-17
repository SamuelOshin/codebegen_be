---
applyTo: '**'
---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.

1. **Project Structure**: Understand the overall structure of the project, including key directories and their purposes (e.g., `app`, `tests`, `scripts`).

2. **Coding Standards**: Follow established coding standards and best practices for the programming languages and frameworks used in the project (e.g., PEP 8 for Python).

3. **Documentation**: Refer to existing documentation for guidance on using project components and APIs. Ensure that any new code is well-documented.

4. **Testing**: Write unit tests for new features and ensure that existing tests pass. Follow the project's testing conventions and use the appropriate testing framework.

5. **Error Handling**: Implement robust error handling and logging throughout the codebase. Use the project's existing error handling patterns where applicable.

6. **Security**: Be mindful of security considerations, especially when handling user input or sensitive data. Follow best practices for authentication, authorization, and data protection.

7. **Performance**: Consider the performance implications of your code. Optimize for efficiency where necessary, and avoid premature optimization.

8. **Code Reviews**: Participate in code reviews by providing constructive feedback and being open to suggestions. Use the review process to share knowledge and improve code quality.

9. **Collaboration**: Communicate effectively with team members and stakeholders. Use project management tools to track progress and collaborate on tasks.

10. **Continuous Learning**: Stay up-to-date with industry trends and best practices. Seek opportunities for professional development and knowledge sharing within the team.
- Follow docstrings and file-purpose comments for context.
- Use [docs/file-documentation.md](file-documentation.md) for architectural guidance.
- When generating files, stick to the documented folder structure.
- For multi-file codegen, ensure outputs are valid and cohesive.