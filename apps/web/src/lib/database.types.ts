export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      account_mappings: {
        Row: {
          account_code: string
          company_id: string | null
          created_at: string
          doc_type: string
          id: string
          office_id: string
          target: string
        }
        Insert: {
          account_code: string
          company_id?: string | null
          created_at?: string
          doc_type: string
          id?: string
          office_id: string
          target: string
        }
        Update: {
          account_code?: string
          company_id?: string | null
          created_at?: string
          doc_type?: string
          id?: string
          office_id?: string
          target?: string
        }
        Relationships: [
          {
            foreignKeyName: "account_mappings_company_id_office_id_fkey"
            columns: ["company_id", "office_id"]
            isOneToOne: false
            referencedRelation: "companies"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "account_mappings_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      assumptions: {
        Row: {
          case_id: string
          choices: Json | null
          confirmed_at: string | null
          confirmed_by: string | null
          created_at: string
          grp: string
          id: string
          justification: string | null
          key: string
          label: string
          office_id: string
          scope: string
          status: string
          suggested_origin: Json
          suggested_value: Json | null
          updated_at: string
          value: Json | null
          value_type: string
        }
        Insert: {
          case_id: string
          choices?: Json | null
          confirmed_at?: string | null
          confirmed_by?: string | null
          created_at?: string
          grp: string
          id?: string
          justification?: string | null
          key: string
          label: string
          office_id: string
          scope: string
          status?: string
          suggested_origin?: Json
          suggested_value?: Json | null
          updated_at?: string
          value?: Json | null
          value_type: string
        }
        Update: {
          case_id?: string
          choices?: Json | null
          confirmed_at?: string | null
          confirmed_by?: string | null
          created_at?: string
          grp?: string
          id?: string
          justification?: string | null
          key?: string
          label?: string
          office_id?: string
          scope?: string
          status?: string
          suggested_origin?: Json
          suggested_value?: Json | null
          updated_at?: string
          value?: Json | null
          value_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "assumptions_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "assumptions_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_events: {
        Row: {
          actor: string | null
          after: Json | null
          before: Json | null
          created_at: string
          entity: string
          entity_id: string | null
          event: string
          id: number
          office_id: string
        }
        Insert: {
          actor?: string | null
          after?: Json | null
          before?: Json | null
          created_at?: string
          entity: string
          entity_id?: string | null
          event: string
          id?: never
          office_id: string
        }
        Update: {
          actor?: string | null
          after?: Json | null
          before?: Json | null
          created_at?: string
          entity?: string
          entity_id?: string | null
          event?: string
          id?: never
          office_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "audit_events_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      companies: {
        Row: {
          cnpj: string
          created_at: string
          id: string
          legal_name: string
          office_id: string
        }
        Insert: {
          cnpj: string
          created_at?: string
          id?: string
          legal_name: string
          office_id: string
        }
        Update: {
          cnpj?: string
          created_at?: string
          id?: string
          legal_name?: string
          office_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "companies_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      extracted_values: {
        Row: {
          account_code: string | null
          bbox: number[]
          case_id: string
          column_name: string | null
          competence: string
          created_at: string
          doc_type: string
          field_key: string
          file_id: string
          id: string
          label: string
          nature: string | null
          office_id: string
          ordinal: number
          page: number
          parser_version: string
          section: string
          value: number
        }
        Insert: {
          account_code?: string | null
          bbox: number[]
          case_id: string
          column_name?: string | null
          competence: string
          created_at?: string
          doc_type: string
          field_key: string
          file_id: string
          id?: string
          label: string
          nature?: string | null
          office_id: string
          ordinal: number
          page: number
          parser_version: string
          section: string
          value: number
        }
        Update: {
          account_code?: string | null
          bbox?: number[]
          case_id?: string
          column_name?: string | null
          competence?: string
          created_at?: string
          doc_type?: string
          field_key?: string
          file_id?: string
          id?: string
          label?: string
          nature?: string | null
          office_id?: string
          ordinal?: number
          page?: number
          parser_version?: string
          section?: string
          value?: number
        }
        Relationships: [
          {
            foreignKeyName: "extracted_values_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "extracted_values_file_id_office_id_fkey"
            columns: ["file_id", "office_id"]
            isOneToOne: false
            referencedRelation: "source_files"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "extracted_values_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      jobs: {
        Row: {
          attempts: number
          created_at: string
          finished_at: string | null
          id: string
          idempotency_key: string
          kind: string
          last_error: string | null
          locked_at: string | null
          office_id: string
          payload: Json
          run_after: string
          status: string
        }
        Insert: {
          attempts?: number
          created_at?: string
          finished_at?: string | null
          id?: string
          idempotency_key: string
          kind: string
          last_error?: string | null
          locked_at?: string | null
          office_id: string
          payload?: Json
          run_after?: string
          status?: string
        }
        Update: {
          attempts?: number
          created_at?: string
          finished_at?: string | null
          id?: string
          idempotency_key?: string
          kind?: string
          last_error?: string | null
          locked_at?: string | null
          office_id?: string
          payload?: Json
          run_after?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "jobs_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      office_members: {
        Row: {
          crc: string | null
          created_at: string
          is_technical_responsible: boolean
          office_id: string
          professional_name: string | null
          role: Database["public"]["Enums"]["member_role"]
          user_id: string
        }
        Insert: {
          crc?: string | null
          created_at?: string
          is_technical_responsible?: boolean
          office_id: string
          professional_name?: string | null
          role?: Database["public"]["Enums"]["member_role"]
          user_id: string
        }
        Update: {
          crc?: string | null
          created_at?: string
          is_technical_responsible?: boolean
          office_id?: string
          professional_name?: string | null
          role?: Database["public"]["Enums"]["member_role"]
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "office_members_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      offices: {
        Row: {
          created_at: string
          id: string
          name: string
          settings: Json
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          settings?: Json
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          settings?: Json
        }
        Relationships: []
      }
      projection_lines: {
        Row: {
          activity: string | null
          amount: number
          base: number
          formula: string
          id: number
          kind: string
          office_id: string
          ordinal: number
          origin: Json
          partial: boolean
          period: string
          projection_id: string
          rate: number
          regime: string
          rule_ref: string
          tax: string
          verified: boolean
        }
        Insert: {
          activity?: string | null
          amount: number
          base: number
          formula: string
          id?: never
          kind: string
          office_id: string
          ordinal: number
          origin?: Json
          partial?: boolean
          period: string
          projection_id: string
          rate: number
          regime: string
          rule_ref: string
          tax: string
          verified?: boolean
        }
        Update: {
          activity?: string | null
          amount?: number
          base?: number
          formula?: string
          id?: never
          kind?: string
          office_id?: string
          ordinal?: number
          origin?: Json
          partial?: boolean
          period?: string
          projection_id?: string
          rate?: number
          regime?: string
          rule_ref?: string
          tax?: string
          verified?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "projection_lines_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "projection_lines_projection_id_office_id_fkey"
            columns: ["projection_id", "office_id"]
            isOneToOne: false
            referencedRelation: "projections"
            referencedColumns: ["id", "office_id"]
          },
        ]
      }
      projections: {
        Row: {
          assumptions: Json
          assumptions_hash: string
          case_id: string
          created_at: string
          decision_hash: string
          decision_version: string
          duration_ms: number | null
          engine_runs: number | null
          error_code: string | null
          error_message: string | null
          id: string
          office_id: string
          recommendation: Json
          requested_by: string | null
          result: Json
          result_hash: string | null
          rules_hash: string
          rules_version: string
          sensitivity: Json
          snapshot_id: string
          snapshot_sha256: string
          status: string
          threshold: number
          year: number
        }
        Insert: {
          assumptions?: Json
          assumptions_hash: string
          case_id: string
          created_at?: string
          decision_hash: string
          decision_version: string
          duration_ms?: number | null
          engine_runs?: number | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id: string
          recommendation?: Json
          requested_by?: string | null
          result?: Json
          result_hash?: string | null
          rules_hash: string
          rules_version: string
          sensitivity?: Json
          snapshot_id: string
          snapshot_sha256: string
          status: string
          threshold: number
          year: number
        }
        Update: {
          assumptions?: Json
          assumptions_hash?: string
          case_id?: string
          created_at?: string
          decision_hash?: string
          decision_version?: string
          duration_ms?: number | null
          engine_runs?: number | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id?: string
          recommendation?: Json
          requested_by?: string | null
          result?: Json
          result_hash?: string | null
          rules_hash?: string
          rules_version?: string
          sensitivity?: Json
          snapshot_id?: string
          snapshot_sha256?: string
          status?: string
          threshold?: number
          year?: number
        }
        Relationships: [
          {
            foreignKeyName: "projections_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "projections_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "projections_snapshot_id_fkey"
            columns: ["snapshot_id"]
            isOneToOne: false
            referencedRelation: "snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      recommendation_events: {
        Row: {
          actor: string | null
          comment: string | null
          created_at: string
          event: string
          id: number
          office_id: string
          recommendation_id: string
        }
        Insert: {
          actor?: string | null
          comment?: string | null
          created_at?: string
          event: string
          id?: never
          office_id: string
          recommendation_id: string
        }
        Update: {
          actor?: string | null
          comment?: string | null
          created_at?: string
          event?: string
          id?: never
          office_id?: string
          recommendation_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "recommendation_events_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recommendation_events_recommendation_id_office_id_fkey"
            columns: ["recommendation_id", "office_id"]
            isOneToOne: false
            referencedRelation: "recommendations"
            referencedColumns: ["id", "office_id"]
          },
        ]
      }
      recommendations: {
        Row: {
          approved_at: string | null
          approved_by: string | null
          case_id: string
          computed_status: string
          created_at: string
          elaborated_by: string | null
          emitted_at: string | null
          id: string
          office_id: string
          pdf_path: string | null
          pdf_sha256: string | null
          projection_id: string
          status: string
          updated_at: string
        }
        Insert: {
          approved_at?: string | null
          approved_by?: string | null
          case_id: string
          computed_status: string
          created_at?: string
          elaborated_by?: string | null
          emitted_at?: string | null
          id?: string
          office_id: string
          pdf_path?: string | null
          pdf_sha256?: string | null
          projection_id: string
          status?: string
          updated_at?: string
        }
        Update: {
          approved_at?: string | null
          approved_by?: string | null
          case_id?: string
          computed_status?: string
          created_at?: string
          elaborated_by?: string | null
          emitted_at?: string | null
          id?: string
          office_id?: string
          pdf_path?: string | null
          pdf_sha256?: string | null
          projection_id?: string
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "recommendations_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "recommendations_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recommendations_projection_id_office_id_fkey"
            columns: ["projection_id", "office_id"]
            isOneToOne: false
            referencedRelation: "projections"
            referencedColumns: ["id", "office_id"]
          },
        ]
      }
      reconciliations: {
        Row: {
          case_id: string
          competence: string
          description: string
          details: Json
          diff: number | null
          id: string
          justification: string | null
          justified_at: string | null
          justified_by: string | null
          left_label: string
          left_value: number | null
          office_id: string
          right_label: string
          right_value: number | null
          rule: string
          status: string
          tolerance: number
          updated_at: string
        }
        Insert: {
          case_id: string
          competence: string
          description: string
          details?: Json
          diff?: number | null
          id?: string
          justification?: string | null
          justified_at?: string | null
          justified_by?: string | null
          left_label: string
          left_value?: number | null
          office_id: string
          right_label: string
          right_value?: number | null
          rule: string
          status: string
          tolerance: number
          updated_at?: string
        }
        Update: {
          case_id?: string
          competence?: string
          description?: string
          details?: Json
          diff?: number | null
          id?: string
          justification?: string | null
          justified_at?: string | null
          justified_by?: string | null
          left_label?: string
          left_value?: number | null
          office_id?: string
          right_label?: string
          right_value?: number | null
          rule?: string
          status?: string
          tolerance?: number
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "reconciliations_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "reconciliations_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_lines: {
        Row: {
          activity: string | null
          amount: number
          base: number
          formula: string
          id: number
          kind: string
          office_id: string
          ordinal: number
          origin: Json
          partial: boolean
          period: string
          rate: number
          regime: string
          rule_ref: string
          simulation_id: string
          tax: string
          verified: boolean
        }
        Insert: {
          activity?: string | null
          amount: number
          base: number
          formula: string
          id?: never
          kind: string
          office_id: string
          ordinal: number
          origin?: Json
          partial?: boolean
          period: string
          rate: number
          regime: string
          rule_ref: string
          simulation_id: string
          tax: string
          verified?: boolean
        }
        Update: {
          activity?: string | null
          amount?: number
          base?: number
          formula?: string
          id?: never
          kind?: string
          office_id?: string
          ordinal?: number
          origin?: Json
          partial?: boolean
          period?: string
          rate?: number
          regime?: string
          rule_ref?: string
          simulation_id?: string
          tax?: string
          verified?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "simulation_lines_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_lines_simulation_id_office_id_fkey"
            columns: ["simulation_id", "office_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id", "office_id"]
          },
        ]
      }
      simulations: {
        Row: {
          assumptions: Json
          assumptions_hash: string
          case_id: string
          created_at: string
          duration_ms: number | null
          error_code: string | null
          error_message: string | null
          id: string
          office_id: string
          requested_by: string | null
          result: Json
          result_hash: string | null
          rules_hash: string
          rules_version: string
          snapshot_id: string
          snapshot_sha256: string
          status: string
        }
        Insert: {
          assumptions?: Json
          assumptions_hash: string
          case_id: string
          created_at?: string
          duration_ms?: number | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id: string
          requested_by?: string | null
          result?: Json
          result_hash?: string | null
          rules_hash: string
          rules_version: string
          snapshot_id: string
          snapshot_sha256: string
          status: string
        }
        Update: {
          assumptions?: Json
          assumptions_hash?: string
          case_id?: string
          created_at?: string
          duration_ms?: number | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id?: string
          requested_by?: string | null
          result?: Json
          result_hash?: string | null
          rules_hash?: string
          rules_version?: string
          snapshot_id?: string
          snapshot_sha256?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulations_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "simulations_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulations_snapshot_id_fkey"
            columns: ["snapshot_id"]
            isOneToOne: false
            referencedRelation: "snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      snapshots: {
        Row: {
          case_id: string
          content: Json
          created_at: string
          created_by: string | null
          id: string
          office_id: string
          sha256: string
        }
        Insert: {
          case_id: string
          content: Json
          created_at?: string
          created_by?: string | null
          id?: string
          office_id: string
          sha256: string
        }
        Update: {
          case_id?: string
          content?: Json
          created_at?: string
          created_by?: string | null
          id?: string
          office_id?: string
          sha256?: string
        }
        Relationships: [
          {
            foreignKeyName: "snapshots_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "snapshots_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      source_files: {
        Row: {
          case_id: string
          cnpj: string | null
          competence: string | null
          created_at: string
          doc_type: string | null
          error_code: string | null
          error_message: string | null
          id: string
          office_id: string
          original_name: string | null
          pages: number | null
          parser_version: string | null
          result_hash: string | null
          sha256: string
          size_bytes: number | null
          status: string
          storage_path: string
          updated_at: string
          uploaded_by: string
        }
        Insert: {
          case_id: string
          cnpj?: string | null
          competence?: string | null
          created_at?: string
          doc_type?: string | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id: string
          original_name?: string | null
          pages?: number | null
          parser_version?: string | null
          result_hash?: string | null
          sha256: string
          size_bytes?: number | null
          status?: string
          storage_path: string
          updated_at?: string
          uploaded_by?: string
        }
        Update: {
          case_id?: string
          cnpj?: string | null
          competence?: string | null
          created_at?: string
          doc_type?: string | null
          error_code?: string | null
          error_message?: string | null
          id?: string
          office_id?: string
          original_name?: string | null
          pages?: number | null
          parser_version?: string | null
          result_hash?: string | null
          sha256?: string
          size_bytes?: number | null
          status?: string
          storage_path?: string
          updated_at?: string
          uploaded_by?: string
        }
        Relationships: [
          {
            foreignKeyName: "source_files_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "source_files_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      tax_cases: {
        Row: {
          company_id: string
          created_at: string
          created_by: string | null
          id: string
          office_id: string
          period_end: string
          period_start: string
          status: string
        }
        Insert: {
          company_id: string
          created_at?: string
          created_by?: string | null
          id?: string
          office_id: string
          period_end: string
          period_start: string
          status?: string
        }
        Update: {
          company_id?: string
          created_at?: string
          created_by?: string | null
          id?: string
          office_id?: string
          period_end?: string
          period_start?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "tax_cases_company_id_office_id_fkey"
            columns: ["company_id", "office_id"]
            isOneToOne: false
            referencedRelation: "companies"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "tax_cases_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      validations: {
        Row: {
          actual: number | null
          case_id: string
          created_at: string
          detail: string | null
          diff: number | null
          expected: number | null
          file_id: string
          id: string
          office_id: string
          rule: string
          status: string
        }
        Insert: {
          actual?: number | null
          case_id: string
          created_at?: string
          detail?: string | null
          diff?: number | null
          expected?: number | null
          file_id: string
          id?: string
          office_id: string
          rule: string
          status: string
        }
        Update: {
          actual?: number | null
          case_id?: string
          created_at?: string
          detail?: string | null
          diff?: number | null
          expected?: number | null
          file_id?: string
          id?: string
          office_id?: string
          rule?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "validations_file_id_office_id_fkey"
            columns: ["file_id", "office_id"]
            isOneToOne: false
            referencedRelation: "source_files"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "validations_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
      value_adjustments: {
        Row: {
          author: string
          case_id: string
          created_at: string
          id: string
          new_value: number
          office_id: string
          old_value: number
          reason: string
          value_id: string
        }
        Insert: {
          author?: string
          case_id: string
          created_at?: string
          id?: string
          new_value: number
          office_id: string
          old_value: number
          reason: string
          value_id: string
        }
        Update: {
          author?: string
          case_id?: string
          created_at?: string
          id?: string
          new_value?: number
          office_id?: string
          old_value?: number
          reason?: string
          value_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "value_adjustments_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "value_adjustments_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "value_adjustments_value_id_fkey"
            columns: ["value_id"]
            isOneToOne: false
            referencedRelation: "effective_values"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "value_adjustments_value_id_fkey"
            columns: ["value_id"]
            isOneToOne: false
            referencedRelation: "extracted_values"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      effective_values: {
        Row: {
          account_code: string | null
          adjusted: boolean | null
          adjusted_at: string | null
          bbox: number[] | null
          case_id: string | null
          column_name: string | null
          competence: string | null
          created_at: string | null
          doc_type: string | null
          effective_value: number | null
          field_key: string | null
          file_id: string | null
          id: string | null
          label: string | null
          last_reason: string | null
          nature: string | null
          office_id: string | null
          ordinal: number | null
          page: number | null
          parser_version: string | null
          section: string | null
          value: number | null
        }
        Relationships: [
          {
            foreignKeyName: "extracted_values_case_id_office_id_fkey"
            columns: ["case_id", "office_id"]
            isOneToOne: false
            referencedRelation: "tax_cases"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "extracted_values_file_id_office_id_fkey"
            columns: ["file_id", "office_id"]
            isOneToOne: false
            referencedRelation: "source_files"
            referencedColumns: ["id", "office_id"]
          },
          {
            foreignKeyName: "extracted_values_office_id_fkey"
            columns: ["office_id"]
            isOneToOne: false
            referencedRelation: "offices"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      approve_recommendation: { Args: { p_id: string }; Returns: undefined }
      assumption_value_ok: {
        Args: { p_choices: Json; p_type: string; p_value: Json }
        Returns: boolean
      }
      confirm_assumption: {
        Args: { p_id: string; p_justification: string; p_value: Json }
        Returns: undefined
      }
      decision_threshold: { Args: { p_office: string }; Returns: number }
      enqueue_job: {
        Args: {
          p_key: string
          p_kind: string
          p_office: string
          p_payload: Json
        }
        Returns: undefined
      }
      homologate_case: {
        Args: { p_case_id: string }
        Returns: {
          sha256: string
          snapshot_id: string
        }[]
      }
      is_admin: { Args: { p_office: string }; Returns: boolean }
      is_member: { Args: { p_office: string }; Returns: boolean }
      is_technical_responsible: { Args: { p_office: string }; Returns: boolean }
      planning_case: {
        Args: { p_case_id: string }
        Returns: {
          company_id: string
          created_at: string
          created_by: string | null
          id: string
          office_id: string
          period_end: string
          period_start: string
          status: string
        }
        SetofOptions: {
          from: "*"
          to: "tax_cases"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      recommendation_for_update: {
        Args: { p_id: string }
        Returns: {
          approved_at: string | null
          approved_by: string | null
          case_id: string
          computed_status: string
          created_at: string
          elaborated_by: string | null
          emitted_at: string | null
          id: string
          office_id: string
          pdf_path: string | null
          pdf_sha256: string | null
          projection_id: string
          status: string
          updated_at: string
        }
        SetofOptions: {
          from: "*"
          to: "recommendations"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      request_calculation: { Args: { p_case_id: string }; Returns: undefined }
      request_planning: { Args: { p_case_id: string }; Returns: undefined }
      request_projection: { Args: { p_case_id: string }; Returns: undefined }
      request_report: { Args: { p_id: string }; Returns: undefined }
      request_simulation_export: {
        Args: { p_simulation_id: string }
        Returns: undefined
      }
      request_xlsx_export: { Args: { p_case_id: string }; Returns: undefined }
      return_recommendation: {
        Args: { p_comment: string; p_id: string }
        Returns: undefined
      }
      set_decision_threshold: {
        Args: { p_office: string; p_threshold: number }
        Returns: undefined
      }
      set_technical_responsible: {
        Args: {
          p_crc: string
          p_flag: boolean
          p_name: string
          p_office: string
          p_user: string
        }
        Returns: undefined
      }
      storage_path_office: { Args: { p_name: string }; Returns: string }
      submit_recommendation: { Args: { p_id: string }; Returns: undefined }
      write_audit: {
        Args: {
          p_after: Json
          p_before: Json
          p_entity: string
          p_entity_id: string
          p_event: string
          p_office: string
        }
        Returns: undefined
      }
    }
    Enums: {
      member_role: "admin" | "analyst"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      member_role: ["admin", "analyst"],
    },
  },
} as const

