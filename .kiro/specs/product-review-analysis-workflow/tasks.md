# Implementation Plan

## Overview

This implementation plan breaks down the Product Review Analysis Workflow into discrete, manageable coding tasks. Each task builds incrementally on previous work, following the design document's architecture.

## Task List

- [ ] 1. Set up core data models and database schema
  - Create Insight data model with all fields (source_agent, insight_text, severity_score, etc.)
  - Update ChatMessageStep model to include `thought` field for reasoning traces
  - Create ExecutionContext model with conversational state fields
  - Add database migration for ChatMessageStep.thought column
  - _Requirements: 1.1, 4.2, 4.3, 4.4, 12.3_

- [ ] 2. Implement tool functions with mock data
  - [ ] 2.1 Create get_user_datasets_with_eda tool
    - Define function signature with user_id parameter
    - Return mock dataset list with EDA metadata (column_stats, summary, insights)
    - Include sample data matching the Netflix review example from requirements
    - _Requirements: 1.4, 5.1, 9.1_
  
  - [ ] 2.2 Create query_reviews tool
    - Define function with filters (rating_filter, date_range, source_filter, text_contains, limit)
    - Return mock review data with proper structure
    - Include query_info metadata
    - _Requirements: 5.2, 5.3, 5.5, 9.2_
  
  - [ ] 2.3 Create semantic_search_reviews tool
    - Define function with query_text and top_k parameters
    - Return mock reviews with similarity scores
    - Simulate vector embedding search results
    - _Requirements: 1.3, 5.4, 9.5_
  
  - [ ] 2.4 Create get_time tool
    - Simple utility function returning current datetime
    - For handling simple informational queries
    - _Requirements: 2.2, 9.3_
  
  - [ ] 2.5 Create generate_visualization tool
    - Define function accepting data, chart_type, title, labels
    - Use Plotly to generate PNG charts
    - Save to static/visualizations directory
    - Return file path for embedding in response
    - _Requirements: 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 9.4_

- [ ] 3. Build Orchestration Layer (Workflow Engine)
  - [ ] 3.1 Create WorkflowOrchestrator class
    - Implement execute_plan method with dependency management
    - Implement execute_step method for single step execution
    - Implement execute_parallel_steps using asyncio.gather
    - Add thread-safe state updates with asyncio.Lock
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 14.1, 14.4_
  
  - [ ] 3.2 Implement execution level builder
    - Create _build_execution_levels method to group steps by dependencies
    - Detect circular dependencies and raise errors
    - Enable parallel execution of independent steps
    - _Requirements: 3.1, 3.2_
  
  - [ ] 3.3 Add retry logic and error handling
    - Implement _execute_step_with_retry method
    - Use RetryConfig for backoff strategy
    - Handle exceptions gracefully and continue with remaining agents
    - Track failed steps in ExecutionContext
    - _Requirements: 14.1, 14.2, 14.4, 14.6, 14.7_
  
  - [ ] 3.4 Implement streaming event emission
    - Add _emit_event method for streaming updates
    - Emit agent_step_start, agent_step_complete, content events
    - Integrate with existing stream_callback pattern
    - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3, 7.4_

- [ ] 4. Implement Coordinator Agent
  - [ ] 4.1 Create CoordinatorAgent class
    - Implement classify_query method using LLM
    - Classify as simple/medium/complex
    - Determine if data retrieval is needed
    - _Requirements: 2.1, 2.2_
  
  - [ ] 4.2 Add query routing logic
    - Route simple queries to direct response
    - Delegate complex queries to Planner Agent
    - Track classification in Chat Message Steps
    - _Requirements: 2.2, 2.3, 4.1_
  
  - [ ] 4.3 Integrate with streaming
    - Emit agent_step_start event on entry
    - Emit agent_step_complete with classification result
    - Save thought and structured_output to database
    - _Requirements: 4.1, 4.2, 7.2_

- [ ] 5. Implement Planner Agent with Iterative ReAct
  - [ ] 5.1 Create PlannerAgent class
    - Implement determine_next_action method
    - Generate ThoughtStep with rationale and alternatives
    - Return NextAction with agent assignment
    - _Requirements: 2.4, 2.5, 2.6, 11.1, 11.2_
  
  - [ ] 5.2 Add query completion detection
    - Implement is_query_complete method
    - Analyze if enough information has been gathered
    - Decide when to trigger synthesis
    - _Requirements: 11.3_
  
  - [ ] 5.3 Implement adaptive planning
    - Use previous_results to inform next action
    - Pivot strategy based on unexpected results
    - Handle empty result sets by broadening criteria
    - _Requirements: 11.3, 11.5, 11.6_
  
  - [ ] 5.4 Add parallel action identification
    - Determine which actions can run concurrently
    - Set can_run_parallel_with field in NextAction
    - Enable orchestrator to batch parallel steps
    - _Requirements: 3.1, 3.2_
  
  - [ ] 5.5 Integrate reasoning traces
    - Save ThoughtStep to Chat Message Steps as thought
    - Save NextAction to Chat Message Steps as structured_output
    - Enable reconstruction of decision flow
    - _Requirements: 4.2, 4.3, 11.4_

- [ ] 6. Implement Data Retrieval Agent
  - [ ] 6.1 Create DataRetrievalAgent class
    - Implement get_user_datasets_with_eda method
    - Call get_user_datasets_with_eda tool
    - Return DatasetWithEDA objects
    - _Requirements: 5.1, 9.1_
  
  - [ ] 6.2 Add query_reviews method
    - Construct filters from parameters
    - Use EDA metadata to optimize queries
    - Call query_reviews tool
    - Handle pagination for large results
    - _Requirements: 5.2, 5.3, 5.5, 5.6_
  
  - [ ] 6.3 Add semantic_search method
    - Call semantic_search_reviews tool
    - Combine with filters if provided
    - Return reviews with similarity scores
    - _Requirements: 5.4_
  
  - [ ] 6.4 Implement EDA-based query optimization
    - Use distinct_count to choose IN vs range queries
    - Use top_values for WHERE clause optimization
    - Use min/max for date range queries
    - _Requirements: 5.6, 13.4_
  
  - [ ] 6.5 Add caching layer
    - Cache frequently accessed datasets
    - Implement cache invalidation on data updates
    - Use Redis for distributed caching
    - _Requirements: 13.1, 13.2_
  
  - [ ] 6.6 Track tool calls in Chat Message Steps
    - Save tool_call with parameters and results
    - Emit streaming events for tool execution
    - _Requirements: 4.2, 7.3, 7.4_

- [ ] 7. Implement Sentiment Analysis Agent
  - [ ] 7.1 Create SentimentAnalysisAgent class
    - Implement analyze_sentiment method
    - Perform overall sentiment classification
    - Perform aspect-based sentiment analysis
    - Generate List[Insight] output
    - _Requirements: 10.1, 10.6_
  
  - [ ] 7.2 Add generate_thought method
    - Create reasoning trace before analysis
    - Explain which aspects will be analyzed and why
    - Save thought to Chat Message Steps
    - _Requirements: 4.2, 11.4_
  
  - [ ] 7.3 Generate sentiment insights
    - Create Insight for each significant finding
    - Include severity_score based on negative sentiment percentage
    - Add visualization_data for charts
    - Include supporting_reviews as evidence
    - _Requirements: 6.1, 6.4, 10.5_
  
  - [ ] 7.4 Add sentiment trend analysis
    - Analyze sentiment changes over time
    - Generate Insight for declining trends
    - Create line chart visualization_data
    - _Requirements: 10.1_

- [ ] 8. Implement Topic Modeling Agent
  - [ ] 8.1 Create TopicModelingAgent class
    - Implement identify_topics method
    - Use LDA or BERTopic for topic extraction
    - Group reviews by topic
    - Generate List[Insight] output
    - _Requirements: 10.2, 10.7_
  
  - [ ] 8.2 Add generate_thought method
    - Explain topic modeling strategy
    - Describe expected number of topics
    - Save reasoning to Chat Message Steps
    - _Requirements: 4.2, 11.4_
  
  - [ ] 8.3 Generate topic insights
    - Create Insight for each significant topic
    - Calculate severity_score based on frequency and rating
    - Add visualization_data for bar charts
    - Include sample reviews and keywords
    - _Requirements: 6.1, 6.4, 10.5_
  
  - [ ] 8.4 Add topic trend detection
    - Identify emerging or declining topics
    - Generate Insight for significant trends
    - Create time-series visualization_data
    - _Requirements: 10.2_

- [ ] 9. Implement Anomaly Detection Agent
  - [ ] 9.1 Create AnomalyDetectionAgent class
    - Implement detect_anomalies method
    - Detect rating spikes and drops
    - Identify unusual topic emergence
    - Generate List[Insight] output
    - _Requirements: 10.3_
  
  - [ ] 9.2 Add generate_thought method
    - Explain anomaly detection strategy
    - Describe baseline calculation approach
    - Save reasoning to Chat Message Steps
    - _Requirements: 4.2, 11.4_
  
  - [ ] 9.3 Generate anomaly insights
    - Create high-severity Insight for each anomaly
    - Include recommended_action in metadata
    - Add visualization_data showing spike
    - Mark as critical if severity > 0.9
    - _Requirements: 6.1, 6.4, 10.5_
  
  - [ ] 9.4 Add source-specific anomaly detection
    - Detect anomalies per review source
    - Identify platform-specific issues
    - _Requirements: 10.3_

- [ ] 10. Implement Summary Agent
  - [ ] 10.1 Create SummaryAgent class
    - Implement summarize_reviews method
    - Support extractive and abstractive summarization
    - Generate List[Insight] output
    - _Requirements: 10.4_
  
  - [ ] 10.2 Add generate_thought method
    - Explain summarization approach
    - Describe key points to extract
    - Save reasoning to Chat Message Steps
    - _Requirements: 4.2, 11.4_
  
  - [ ] 10.3 Generate summary insights
    - Create overview Insight with key points
    - Include supporting_reviews
    - Add confidence_score
    - _Requirements: 6.1, 6.4, 10.5_

- [ ] 11. Implement Synthesis Agent
  - [ ] 11.1 Create SynthesisAgent class
    - Implement synthesize_response method
    - Accept List[Insight] instead of complex dict
    - Generate markdown response
    - _Requirements: 3.3, 3.4, 3.7, 6.1_
  
  - [ ] 11.2 Add generate_synthesis_plan method
    - Create SynthesisThought with outline
    - Identify key insights to highlight
    - Plan visualization placements
    - Choose narrative strategy
    - _Requirements: 3.3, 3.7_
  
  - [ ] 11.3 Implement insight prioritization
    - Sort insights by severity_score
    - Group insights by theme
    - Select top 3-5 for key findings section
    - _Requirements: 3.7_
  
  - [ ] 11.4 Add visualization embedding
    - Call Visualization Agent for charts
    - Embed image paths in markdown
    - Add explanatory text around visualizations
    - _Requirements: 6.2, 6.3_
  
  - [ ] 11.5 Add source citations
    - Extract supporting_reviews from insights
    - Format as citations with excerpts
    - Add to "Supporting Evidence" section
    - _Requirements: 6.4_
  
  - [ ] 11.6 Save synthesis thought to Chat Message Steps
    - Store SynthesisThought as structured_output
    - Enable transparency in synthesis decisions
    - _Requirements: 4.2, 11.4_

- [ ] 12. Implement Visualization Agent
  - [ ] 12.1 Create VisualizationAgent class
    - Implement generate_visualization method
    - Support bar, line, pie, scatter chart types
    - Use Plotly for chart generation
    - _Requirements: 8.1, 8.5_
  
  - [ ] 12.2 Add chart generation logic
    - Create Plotly figures based on chart_type
    - Apply consistent styling and templates
    - Add titles, labels, and legends
    - _Requirements: 8.6_
  
  - [ ] 12.3 Implement PNG export
    - Save charts to static/visualizations directory
    - Generate unique filenames with UUID
    - Return file path for embedding
    - _Requirements: 8.2, 8.3_
  
  - [ ] 12.4 Add visualization metadata tracking
    - Store visualization info in Chat Message Steps
    - Track chart_type, title, and filepath
    - _Requirements: 4.2, 8.4_

- [ ] 13. Implement Conversational Context Manager
  - [ ] 13.1 Create ConversationalContextManager class
    - Implement save_context method
    - Store insights and agent_outputs in Redis
    - Associate with session_id
    - _Requirements: 12.1, 12.2_
  
  - [ ] 13.2 Add load_context method
    - Retrieve previous context from Redis
    - Reconstruct ExecutionContext
    - _Requirements: 12.6_
  
  - [ ] 13.3 Implement follow-up query detection
    - Use LLM to detect references to previous results
    - Check for keywords like "that", "the biggest", "compare"
    - _Requirements: 12.6_
  
  - [ ] 13.4 Add context-aware planning
    - Pass previous context to Planner Agent
    - Enable reuse of cached results
    - Generate simpler plans for follow-ups
    - _Requirements: 12.6_

- [ ] 14. Implement main workflow integration
  - [ ] 14.1 Create ProductReviewAnalysisWorkflow class
    - Extend LlamaIndex Workflow base class
    - Define workflow steps as @step methods
    - Integrate all agents
    - _Requirements: 2.1, 2.3, 3.1, 3.2_
  
  - [ ] 14.2 Add coordinator step
    - Call CoordinatorAgent.classify_query
    - Route to appropriate handler
    - Emit streaming events
    - _Requirements: 2.1, 2.2, 7.1, 7.2_
  
  - [ ] 14.3 Add iterative planning loop
    - Call PlannerAgent.determine_next_action
    - Execute action via Orchestrator
    - Check if query is complete
    - Repeat until complete
    - _Requirements: 2.4, 2.5, 11.1, 11.2, 11.3_
  
  - [ ] 14.4 Add parallel execution step
    - Identify parallel actions from Planner
    - Pass to Orchestrator.execute_parallel_steps
    - Collect results safely
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 14.5 Add synthesis step
    - Collect all insights from context
    - Call SynthesisAgent.synthesize_response
    - Stream final response
    - _Requirements: 3.3, 6.1, 7.5_
  
  - [ ] 14.6 Integrate Chat Message Step tracking
    - Save each agent's thought and action
    - Track step_order correctly
    - Store in database immediately
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ] 14.7 Add conversational context integration
    - Load previous context at workflow start
    - Save context after workflow completion
    - Enable follow-up query handling
    - _Requirements: 12.1, 12.2, 12.3_

- [ ] 15. Create API endpoint for workflow
  - [ ] 15.1 Add POST /api/v1/chat/analyze endpoint
    - Accept ChatRequest with message and session_id
    - Create assistant message in database
    - Initialize ProductReviewAnalysisWorkflow
    - Return streaming response
    - _Requirements: 7.1, 7.5, 7.6_
  
  - [ ] 15.2 Implement streaming response handler
    - Use FastAPI StreamingResponse
    - Stream agent steps and content
    - Handle errors gracefully
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ] 15.3 Add GET /api/v1/chat/steps/{message_id} endpoint
    - Retrieve Chat Message Steps for a message
    - Return in chronological order
    - Include thoughts, actions, and results
    - _Requirements: 4.6_
  
  - [ ] 15.4 Add user authentication and authorization
    - Verify user owns the session
    - Check user has access to datasets
    - Implement rate limiting
    - _Requirements: 13.1, 13.2, 13.3_

- [ ] 16. Add feedback collection system
  - [ ] 16.1 Create feedback data model
    - Add FeedbackRecord model
    - Store rating, comment, and execution trace
    - Link to message_id
    - _Requirements: 12.1, 12.2_
  
  - [ ] 16.2 Add POST /api/v1/feedback endpoint
    - Accept user rating and optional comment
    - Store with associated Chat Message Steps
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ] 16.3 Add feedback analytics
    - Track feedback scores per agent type
    - Identify patterns in positive/negative feedback
    - Expose metrics for monitoring
    - _Requirements: 12.4, 12.6_
  
  - [ ] 16.4 Integrate feedback into planning
    - Pass feedback_history to Planner Agent
    - Use historical patterns to improve decisions
    - _Requirements: 12.5, 12.6_

- [ ] 17. Add performance optimizations
  - [ ] 17.1 Implement query result caching
    - Cache query_reviews results in Redis
    - Use query hash as cache key
    - Set TTL based on data freshness requirements
    - _Requirements: 13.1, 13.2_
  
  - [ ] 17.2 Add database query optimization
    - Create indexes on frequently queried fields
    - Use database-level aggregations
    - Implement pagination for large result sets
    - _Requirements: 13.4, 13.5, 13.6_
  
  - [ ] 17.3 Add slow query logging
    - Track query execution times
    - Log queries exceeding threshold
    - Enable performance analysis
    - _Requirements: 13.7_
  
  - [ ] 17.4 Implement materialized views for large datasets
    - Create views for main review tables > 100k rows
    - Refresh on data updates
    - _Requirements: 13.3_

- [ ] 18. Add monitoring and observability
  - [ ] 18.1 Add execution time tracking
    - Track duration for each agent step
    - Store in Chat Message Steps
    - Expose metrics endpoint
    - _Requirements: 4.1, 4.5_
  
  - [ ] 18.2 Add error rate monitoring
    - Track agent failure rates
    - Monitor retry attempts
    - Alert on high error rates
    - _Requirements: 14.1, 14.2_
  
  - [ ] 18.3 Add cache hit rate monitoring
    - Track cache hits vs misses
    - Monitor cache effectiveness
    - _Requirements: 13.1_
  
  - [ ] 18.4 Add user feedback metrics
    - Track average feedback scores
    - Monitor feedback trends
    - Identify problematic query patterns
    - _Requirements: 12.4_

- [ ]* 19. Write integration tests
  - Test complete workflow with sample queries
  - Test parallel agent execution
  - Test ReAct loop with simulated failures
  - Test conversational context persistence
  - Test streaming response generation
  - _Requirements: All_

- [ ]* 20. Write documentation
  - Document API endpoints with examples
  - Document agent architecture and flow
  - Document tool functions and parameters
  - Create deployment guide
  - _Requirements: All_
